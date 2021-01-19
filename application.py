from flask import Flask, render_template, request, redirect, url_for
from flask_cors import CORS
import braintree
import json
import uuid

application = app = Flask(__name__)
CORS(app)

#gateway Settings
gateway = braintree.BraintreeGateway(
    braintree.Configuration(
        braintree.Environment.Sandbox,
        merchant_id="9dxqqftdw4x6jfbr",
        public_key="jvh5brdvvfkp5sc8",
        private_key="3ede1f4c980113e88173b110124f3607"
    )
)

#statuses
TRANSACTION_SUCCESS_STATUSES = [
    braintree.Transaction.Status.Authorized,
    braintree.Transaction.Status.Authorizing,
    braintree.Transaction.Status.Settled,
    braintree.Transaction.Status.SettlementConfirmed,
    braintree.Transaction.Status.SettlementPending,
    braintree.Transaction.Status.Settling,
    braintree.Transaction.Status.SubmittedForSettlement
]

#for quick testing purpose, hardcoded customer id
customerId = "clk"

@app.route("/", methods=["GET"])
def index():
#for quick testing purpose, hardcoded customer id
    clientToken = getClientToken(customerId)
    return render_template("checkout-page.html", clientToken=clientToken, customerId=customerId)

def getClientToken(customerId):
    isExistingCustomer = findCustomer(customerId)
    if(isExistingCustomer):
        clientToken = gateway.client_token.generate({
            "customer_id": customerId
        })
    else:
        clientToken = gateway.client_token.generate({})
    print("Client token created for existing customer: " + str(isExistingCustomer))
    print(clientToken)
    return clientToken

def findCustomer(customerId):
    print("checking existance of customer id: " + customerId)
    try:    
        customer = gateway.customer.find(customerId)
        print("  customer id {} found!".format(customerId))
        return True
    except braintree.exceptions.not_found_error.NotFoundError as e:
        print("  customer id {} NOT found!".format(customerId))
        return False


@app.route("/checkout", methods=["POST"])
def createPayment():
    nonce_from_the_client = request.form["payment_method_nonce"]
    print("nonce: " + nonce_from_the_client) 
    customerId = request.form["cust_id"]
    amount = request.form["amount"]
    return createTransaction(nonce_from_the_client, customerId, amount)

def createTransaction(nonce_from_the_client, customerId, amount):
    isExistingCustomer = findCustomer(customerId)
    tranReq = formulateTransactionRequest(isExistingCustomer, customerId, nonce_from_the_client, amount)
    orderId = tranReq["order_id"]
    # implement in such a way that always store card info in vault for customer (new and returning)
    result = gateway.transaction.sale(tranReq)
    if result.is_success:
        print("Transaction is processed successfully:")
        print("  Transaction id: {}, Order id: {}".format(result.transaction.id, orderId))
        return redirect(url_for("showSuccessfulTransaction",transaction_id=result.transaction.id))       
    elif result.transaction:
        print("Error processing transaction:")
        print("  Transaction id: {}, Order id: {}".format(result.transaction.id, orderId))
        print("  Error Code: {}, Error Message: {}".format(result.transaction.processor_response_code, result.transaction.processor_response_text))
        return redirect(url_for("errorProcessingPage",orderId=orderId))   
    else:
        print("Validation error:")
        print("  Transaction id: {}, Order id: {}".format(None, orderId))
        for x in result.errors.deep_errors: 
            print("  Error Attribute: {}, Error Code: {}, Error Message: {}".format(x.attribute, x.code, x.message))
        return redirect(url_for("errorProcessingPage",orderId=orderId))       

def formulateTransactionRequest(isExistingCustomer, customerId, nonce_from_the_client, amount):
    baseOb = {
        "amount": amount,
        "payment_method_nonce": nonce_from_the_client,
        "order_id": customerId + "-" + str(uuid.uuid1()),
#        "customer": {
#            "id": "steventest"
#        },
        "options": {
            "submit_for_settlement": True,
		    "store_in_vault_on_success": True
        }
    }
    if(not isExistingCustomer):
        cusOb = {"id": customerId}
        baseOb["customer"] = cusOb
    print ("Transaction request obj: ")
    print (baseOb)
    return baseOb

@app.route("/checkouts/<transaction_id>", methods=["GET"])
def showSuccessfulTransaction(transaction_id):
    transaction = gateway.transaction.find(transaction_id) 
    return render_template("paymentResultPage.html", transaction=transaction, isSuccess=True, orderId=transaction.order_id)

@app.route("/error/<orderId>", methods=["GET"])
def errorProcessingPage(orderId):
    return render_template("paymentResultPage.html", orderId=orderId, isSuccess=False)


@app.route("/user/current", methods=["PUT"])
def setCurrentActiveUser():
#for quick demo purposes, exposing API to update active customer id 
    global customerId
    jsonReq = request.get_json()
    customerId = jsonReq['username']
    return customerId

# Run the backend app
if __name__ == "__main__":
    app.run(debug=True)
#    app.run(debug=True, host="0.0.0.0", port=50000)

