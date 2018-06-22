import webapp2
import json
import string
import os
import jinja2
import urllib
import random
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import types
import requests
import requests_toolbelt.adapters.appengine

CLIENT_ID = "146648366291-pb49fenu97l3kurt1es022i62nt91u0r.apps.googleusercontent.com"
CLIENT_SECRET = "kah1W0kZ3EjQcCePjkziv_fJ"
OAUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
STATE = "tj921jklfjsaij21n"
#REDIRECT_URL = "https://finalproject-206401.appspot.com/oAuth"
REDIRECT_URL = "http://localhost:8080/oAuth"
#PROJECT_URL = "https://finalproject-206401.appspot.com"
PROJECT_URL = "http://localhost:8080"

#Required to use Request Library
requests_toolbelt.adapters.appengine.monkeypatch()

#Code taken from Stack Overflow Link: https://stackoverflow.com/questions/16280496/patch-method-handler-on-google-appengine-webapp2
#Allows PATCH option
allowed_methods = webapp2.WSGIApplication.allowed_methods
new_allowed_methods = allowed_methods.union(('PATCH',))
webapp2.WSGIApplication.allowed_methods = new_allowed_methods


# Code taken from Stack Overflow Link: https://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits-in-python
def idGenerator(size=5, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

# Define Stock Entity
class Stock(ndb.Model):
    ticker = ndb.StringProperty(required=True)
    amount = ndb.IntegerProperty(required=True)

# Define Portfolio Entity
class Portfolio(ndb.Model):
    id = ndb.StringProperty(required = True)
    name = ndb.StringProperty()
    owner = ndb.StringProperty()
    stock_portfolio = ndb.StructuredProperty(Stock, repeated=True)
    net_worth = ndb.FloatProperty()

# Define User Entity
# User Identity Tracked Through userURL
class User(ndb.Model):
    id = ndb.StringProperty()
    userURL = ndb.StringProperty(required=True)
    access_token = ndb.StringProperty(required=True)
    fname = ndb.StringProperty()
    lname = ndb.StringProperty()
    email = ndb.StringProperty()
    portfolio = ndb.StringProperty(repeated=True)

#Get List of Valid Symbols
def getValidTicker():
    symbolList = []
    apiLink = "https://api.iextrading.com/1.0"
    getLink = apiLink + "/ref-data/symbols"
    getResult = requests.get(getLink)
    jsonResult = json.loads(getResult.text)
    symbolList = []
    for stock in jsonResult:
        symbolList.append(stock["symbol"])
    return symbolList

#Check if access token is valid
def checkAccess(token, userID):
    userObj = ndb.Key(User, userID).get()
    userAccessToken = "Bearer " + userObj.access_token
    if userAccessToken != token:
        return False
    else:
        return True

#Check if Ticker is Valid
def isValidTicker(stock_ticker):
    if stock_ticker in symbolList:
        return True
    else:
        return False

#Interface with API to get JSON Object for the Price of the Stock
def getStockPrice(stock_ticker):
    apiLink = "https://api.iextrading.com/1.0"
    getLink = apiLink + "/stock/" + stock_ticker + "/price"
    getResult = requests.get(getLink)
    return (getResult.text)

#Check if User Exists
def checkUserID(ID):
    #Retreive Array of User Object
    UserList = User.query()
    li = []
    for entity in UserList:
        li.append(entity.id)
    if (ID not in li):
        return False
    else:
        return True

#Check if Portfolio Exists
def checkPortfolioID(ID):
    #Retreive Array of Portfolio Objects
    PortfolioList = Portfolio.query()
    li = []
    for entity in PortfolioList:
        li.append(entity.id)
    if (ID not in li):
        return False
    else:
        return True

#Check for User URL
def checkUserURL(URL):
    #Retreive Array of User Object
    UserList = User.query()
    li = []
    for entity in UserList:
        li.append(entity.userURL)
    if (URL not in li):
        return False
    else:
        return True

#Get UserID from URL
def getUserID(URL):
    #Retreive Array of User Object
    UserList = User.query()
    for entity in UserList:
        if (entity.userURL == URL):
            return entity.id

#Calculate Portfolio Net Worth, Takes List of Stock Object as Parameter
def getNetWorth(li):
    worth = 0.0
    apiLink = "https://api.iextrading.com/1.0"
    #Parses Through Each Object
    for stock in li:
        stock_ticker = stock.ticker
        stockPriceLink = apiLink + "/stock/" + stock_ticker + "/price"
        getResult = requests.get(stockPriceLink)
        stockPrice = float(getResult.text)
        worth += (stockPrice * stock.amount)
    a = "%.2f" %worth
    return float(a)

class MainPageHandler(webapp2.RequestHandler):
    def get(self):
        url = OAUTH_URL
        url += "?response_type=code&"
        url += "client_id=" + CLIENT_ID
        url += "&redirect_uri=" + REDIRECT_URL
        url += "&scope=email"
        url += "&state=" + STATE
        template_values = {
            'OAuth': url,
        }
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
                                 extensions=['jinja2.ext.autoescape'], autoescape=True)
        template = env.get_template('index.html')
        self.response.write(template.render(template_values))


class OAuthHandler(webapp2.RequestHandler):
    def get(self):
        # Get Authorization Code and State
        authorizationCode = self.request.GET['code']
        state = self.request.GET['state']

        post_body = {
            "code": authorizationCode,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URL,
            "grant_type": "authorization_code"
        }

        post_body = urllib.urlencode(post_body)
        postURL = "https://www.googleapis.com/oauth2/v4/token"

        # Post to Server
        result = urlfetch.fetch(
            url=postURL, payload=post_body, method=urlfetch.POST)
        # Get POST Results from Server
        resultContent = json.loads(result.content)

        APIkey = resultContent["access_token"]

        template_values = {
            'access_token': APIkey
        }

        GoogleURL = "https://www.googleapis.com/plus/v1/people/me"

        header = {
            "Authorization": "Bearer" + " " + APIkey,
        }

        getResult = urlfetch.fetch(
            url=GoogleURL, payload=None, headers=header, method=urlfetch.GET)
        getContent = json.loads(getResult.content)

        # Get the User Info From Google+ API
        fname = getContent["name"]["givenName"]
        lname = getContent["name"]["familyName"]
        email = getContent["emails"][0]["value"]
        userURL = getContent["url"]
        access_token = APIkey

        if (checkUserURL(userURL) == True):
            #User Already Exists, Update Access Key Using Patch
            userID = getUserID(userURL)
            patchURL = PROJECT_URL + "/user/" + userID
            #headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            body_data = {
                "access_token": access_token
            }
            '''
            form_data = urllib.urlencode(body_data)
            patchResult = urlfetch.fetch(
                url = patchURL, payload = form_data, headers = headers, method = urlfetch.PATCH 
            )
            '''
            patchResult = requests.put(url = patchURL, json = body_data)
            self.response.write(patchResult.text)
            self.response.set_status(patchResult.status_code)
        else:
            #Create New User, Create New User Using Post
            #headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            post_url = PROJECT_URL + "/user"
            body_data = {
                "fname": fname,
                "lname": lname,
                "email": email,
                "userURL": userURL,
                "access_token": access_token
            }
            postResult = requests.post(url = post_url, json = body_data)
            '''
            form_data = urllib.urlencode(body_data)
            postResult = urlfetch.fetch(
                url=post_url, payload = form_data, headers = headers, method=urlfetch.POST
            )
            '''

            self.response.write(postResult.text)
            self.response.set_status(postResult.status_code)
        '''
        newBody = [fname, lname, email, access_token, userURL]

        self.response.write(json.dumps(newBody))
        '''
        '''
        env = jinja2.Environment(loader = jinja2.FileSystemLoader(os.path.dirname(__file__)),
                extensions=['jinja2.ext.autoescape'], autoescape = True)
        template = env.get_template('oAuth.html')
        self.response.write(template.render(template_values))
        '''


class UserHandler(webapp2.RequestHandler):
    def post(self):
        # Gets Request Data
        userData = json.loads(self.request.body)
        dataKeys = list(userData.keys())
        userElements = ["fname", "lname", "access_token", "email", "userURL"]
        if (len(dataKeys) != 5 or all(elem in dataKeys for elem in userElements) != True):
            self.response.set_status(400)
        else:
            # Generate User ID
            userID = idGenerator()
            # Create New User
            newUser = User(id=userID, fname=userData["fname"], lname=userData["lname"],
                           access_token=userData["access_token"], email=userData["email"], userURL=userData["userURL"])
            newUser.portfolio = []
            # Create User with UserID as Key
            newUser.key = ndb.Key(User, userID)
            # Update Database
            newUser.put()
            self.response.write(json.dumps(newUser.to_dict()))
            self.response.set_status(201)
    def get(self):
        #Retreives an Array of all User Objects in DataBase
        query = User.query()
        #Create Array to Hold Data
        li = []
        #Loop Through Objects Held in Query, Convert to Dictionary Object and Append to List
        for entity in query:
            #Convert Entity to Dictionary and Remove Unneeded Data
            entity_dict = entity.to_dict()
            del entity_dict["access_token"]
            del entity_dict["email"]
            del entity_dict["userURL"]
            del entity_dict["portfolio"]
            li.append(entity_dict)
        #Turn List into JSON
        self.response.write(json.dumps(li))


class SpecificUserHandler(webapp2.RequestHandler):
    def put(self, id):
        if checkUserID(id):
            # Get User Object
            userObj = ndb.Key(User, id).get()
            # Get New Data, Stored as a Dictionary
            new_data = json.loads(self.request.body)
            newDataKeys = list(new_data.keys())
            # Modifiable User Elements
            userElements = ["fname", "lname", "access_token", "email"]
            # Check and Validate New Data
            if (len(new_data) <= 4 and all(elem in userElements for elem in newDataKeys)):
                for key, value in new_data.iteritems():
                    if (key == "fname"):
                        if (isinstance(value, types.UnicodeType)):
                            userObj.fname = value
                        else:
                            self.response.set_status(400)
                            break
                    elif (key == "lname"):
                        if (isinstance(value, types.UnicodeType)):
                            userObj.lname = value
                        else:
                            self.response.set_status(400)
                            break
                    elif (key == "access_token"):
                        if (isinstance(value, types.UnicodeType)):
                            userObj.access_token = value
                        else:
                            self.response.set_status(400)
                            break
                    elif (key == "email"):
                        if (isinstance(value, types.UnicodeType)):
                            userObj.email = value
                        else:
                            self.response.set_status(400)
                            break
                # Update User Object
                userObj.put()
                self.response.write(json.dumps(userObj.to_dict()))
            else:
                self.response.set_status(400)
        else:
            self.response.set_status(404)
    def get(self, id):
        if checkUserID(id):
            headers = self.request.headers
            headerKeys = []
            for entity in headers:
                headerKeys.append(entity)
            if "Authorization" in headerKeys:
                Token = headers["Authorization"]
                if checkAccess(Token, id):
                    #Get User Object
                    userObj = ndb.Key(User, id).get()
                    #Write User Data
                    self.response.write(json.dumps(userObj.to_dict()))
                else:
                    self.response.set_status(403)
            else:
                self.response.set_status(403)
        else:
            self.response.write("User Not Found")
            self.response.set_status(404)
    def delete(self, id):
        if checkUserID(id):
            headers = self.request.headers
            headerKeys = []
            for entity in headers:
                headerKeys.append(entity)
            if "Authorization" in headerKeys:
                Token = headers["Authorization"]
                if checkAccess(Token, id):
                    userKey = ndb.Key(User, id)
                    userObj = userKey.get()
                    #Check if User has Items in Portfolio
                    if len(userObj.portfolio) != 0:
                        #Remove User From Portfolio
                        for portfolioID in userObj.portolio:
                            portfolioObj = ndb.Key(Portfolio, portfolioID).get()
                            portfolioObj.owner = None
                            portfolioObj.put()
                    userKey.delete()
                    self.response.set_status(204)
                else:
                    self.response.set_status(403)
            else:
                self.response.set_status(403)
        else:
            self.response.set_status(404)
    def patch(self, id):
        if checkUserID(id):
            headers = self.request.headers
            headerKeys = []
            for entity in headers:
                headerKeys.append(entity)
            if "Authorization" in headerKeys:
                Token = headers["Authorization"]
                if checkAccess(Token, id):
                    # Get User Object
                    userObj = ndb.Key(User, id).get()
                    # Get New Data, Stored as a Dictionary
                    new_data = json.loads(self.request.body)
                    newDataKeys = list(new_data.keys())
                    # Modifiable User Elements
                    userElements = ["fname", "lname", "access_token", "email"]
                    # Check and Validate New Data
                    if (len(new_data) <= 4 and all(elem in userElements for elem in newDataKeys)):
                        for key, value in new_data.iteritems():
                            if (key == "fname"):
                                if (isinstance(value, types.UnicodeType)):
                                    userObj.fname = value
                                else:
                                    self.response.set_status(400)
                                    break
                            elif (key == "lname"):
                                if (isinstance(value, types.UnicodeType)):
                                    userObj.lname = value
                                else:
                                    self.response.set_status(400)
                                    break
                            elif (key == "access_token"):
                                if (isinstance(value, types.UnicodeType)):
                                    userObj.access_token = value
                                else:
                                    self.response.set_status(400)
                                    break
                            elif (key == "email"):
                                if (isinstance(value, types.UnicodeType)):
                                    userObj.email = value
                                else:
                                    self.response.set_status(400)
                                    break
                        # Update User Object
                        userObj.put()
                        self.response.write(json.dumps(userObj.to_dict()))
                else:
                    self.response.set_status(403)
            else:
                self.response.set_status(403)
        else:
            self.response.set_status(404)

class PortfolioHandler(webapp2.RequestHandler):
    def post(self):
        #Get Data From the Post Request
        portfolioData = json.loads(self.request.body)
        portfolioKeys = list(portfolioData.keys())
        portfolioElements = ["name", "stock_portfolio"]
        break_flag = False
        if (len(portfolioKeys) > 2 or all(elem in portfolioElements for elem in portfolioData) != True):
            print("Error with Keys")
            break_flag = True
            self.response.set_status(400)
        else:
            portfolioID = idGenerator()
            validTickers = getValidTicker()
            stockElements = ["ticker", "amount"]
            #Create Portfolio Object
            newPortfolio = Portfolio(id = portfolioID, stock_portfolio = [])
            for key, value in portfolioData.iteritems():
                if (key == "name"):
                    if(isinstance(value, types.UnicodeType)):
                        newPortfolio.name = value
                    else:
                        break_flag = True
                        print("Error with Name Type")
                        self.response.set_status(400)
                        break
                elif (key == "stock_portfolio"):
                    #Only One Object Since it is a Dictionary
                    if(isinstance(value, types.DictType)):
                        Stock_Keys = list(value.keys())
                        #Check that Dictionary has the Correct Elements
                        if (len(Stock_Keys) != 2 or all (elem in value for elem in stockElements) != True):
                            break_flag = True
                            self.response.set_status(400)
                            break
                        else:
                            if (value["ticker"] not in validTickers or isinstance(value["amount"], types.IntType) != True):
                                break_flag = True
                                self.response.set_status(400)
                                break
                            else:
                                newStock = Stock(ticker = value["ticker"], amount = value["amount"])
                                newPortfolio.stock_portfolio.append(newStock)
                    #Object is a List of Stocks
                    elif (isinstance(value, types.ListType)):
                        #Iterate Through Each Object in the List
                        for element in value:
                            Stock_Keys = list(element.keys())
                            if (len(Stock_Keys) != 2 or all (elem in Stock_Keys for elem in stockElements) != True):
                                break_flag = True
                                self.response.set_status(400)
                                break
                            else:
                                if (element["ticker"] not in validTickers or isinstance(element["amount"], types.IntType) != True):
                                    break_flag = True
                                    self.response.set_status(400)
                                    break
                                else:
                                    newStock = Stock(ticker = element["ticker"], amount = element["amount"])
                                    newPortfolio.stock_portfolio.append(newStock)
                    elif (isinstance(value, types.NoneType)):
                        break
                    else:
                        self.response.set_status(400)
        if break_flag == False:
            #Update Net Worth
            newPortfolio.net_worth = getNetWorth(newPortfolio.stock_portfolio)
            #Set Portfolio Key to be Portfolio ID and Update Server
            newPortfolio.key = ndb.Key(Portfolio, portfolioID)
            newPortfolio.put()
            print(newPortfolio)
            self.response.write(json.dumps(newPortfolio.to_dict()))
            self.response.set_status(201)
    def get(self):
        #Get All Available Portfolios
        queryPortfolio = Portfolio.query()
        PortfolioList = []
        for objects in queryPortfolio:
            modifiedPortfolio = objects.to_dict()
            del modifiedPortfolio["owner"]
            del modifiedPortfolio["net_worth"]
            del modifiedPortfolio["stock_portfolio"]
            PortfolioList.append(modifiedPortfolio)
        self.response.write(json.dumps(PortfolioList))

class UserPortfolioHandler(webapp2.RequestHandler):
    def put(self, userID, portfolioID):
        if checkUserID(userID) and checkPortfolioID(portfolioID):
            #Check Access Token
            headers = self.request.headers
            headerKeys = []
            for entity in headers:
                headerKeys.append(entity)
            if "Authorization" in headerKeys:
                Token = headers["Authorization"]
                if checkAccess(Token, userID):
                    #Check if Portfolio Taken
                    portfolioKey = ndb.Key(Portfolio, portfolioID)
                    portfolioObj = portfolioKey.get()
                    if portfolioObj.owner == None:
                        portfolioObj.owner = userID
                        userKey = ndb.Key(User, userID)
                        userObj = userKey.get()
                        userObj.portfolio.append(portfolioID)
                        #Update Portfolio and User
                        portfolioObj.put()
                        userObj.put()
                        self.response.set_status(204)
                    else:
                        print(type(portfolioObj.owner))
                        self.response.write("Portfolio Already Taken")
                        self.response.set_status(403)
            else:
                self.response.write("Unauthorized Access")
                self.response.set_status(403)
        else:
            print("Error Here")
            self.response.write("User or Portfolio Does Not Exist")
            self.response.set_status(404)
    def delete(self, userID, portfolioID):
        if checkUserID(userID) and checkPortfolioID(portfolioID):
            #Check Access Token
            headers = self.request.headers
            headerKeys = []
            for entity in headers:
                headerKeys.append(entity)
            if "Authorization" in headerKeys:
                Token = headers["Authorization"]
                if checkAccess(Token, userID):
                    #Check if Portfolio Taken
                    portfolioKey = ndb.Key(Portfolio, portfolioID)
                    portfolioObj = portfolioKey.get()
                    if portfolioObj.owner == userID:
                        portfolioObj.owner = None
                        userKey = ndb.Key(User, userID)
                        userObj = userKey.get()
                        #Remove Portfolio ID from User's Portfolio
                        userObj.portfolio.remove(portfolioID)
                        #Update Portfolio and User
                        portfolioObj.put()
                        userObj.put()
                        self.response.set_status(204)
                    else:
                        self.response.write("Portfolio Does Not Belong to User")
                        self.response.set_status(403)
            else:
                self.response.write("Unauthorized Access")
                self.response.set_status(403)
        else:
            self.response.write("User or Portfolio Does Not Exist")
            self.response.set_status(404)
    def patch(self, userID, portfolioID):
        if checkUserID(userID) and checkPortfolioID(portfolioID):
            #Check Access Token
            headers = self.request.headers
            headerKeys = []
            for entity in headers:
                headerKeys.append(entity)
            if "Authorization" in headerKeys:
                Token = headers["Authorization"]
                if checkAccess(Token, userID):
                    #Check if Portfolio Taken
                    portfolioKey = ndb.Key(Portfolio, portfolioID)
                    portfolioObj = portfolioKey.get()
                    if portfolioObj.owner == userID:
                        #Get Data From the Post Request
                        portfolioData = json.loads(self.request.body)
                        portfolioKeys = list(portfolioData.keys())
                        portfolioElements = ["name", "stock_portfolio"]
                        break_flag = False
                        if (len(portfolioKeys) > 2 or all(elem in portfolioElements for elem in portfolioData) != True):
                            print("Error with Keys")
                            break_flag = True
                            self.response.set_status(400)
                        else:
                            validTickers = getValidTicker()
                            stockElements = ["ticker", "amount"]
                            for key, value in portfolioData.iteritems():
                                if (key == "name"):
                                    if(isinstance(value, types.UnicodeType)):
                                        portfolioObj.name = value
                                    else:
                                        break_flag = True
                                        print("Error with Name Type")
                                        self.response.set_status(400)
                                        break
                                if (key == "stock_portfolio"):
                                    #Empty Out Old Portfolio Object
                                    del portfolioObj.stock_portfolio[:]
                                    #Only One Object Since it is a Dictionary
                                    if(isinstance(value, types.DictType)):
                                        Stock_Keys = list(value.keys())
                                        #Check that Dictionary has the Correct Elements
                                        if (len(Stock_Keys) != 2 or all (elem in value for elem in stockElements) != True):
                                            break_flag = True
                                            self.response.set_status(400)
                                            break
                                        else:
                                            if (value["ticker"] not in validTickers or isinstance(value["amount"], types.IntType) != True):
                                                break_flag = True
                                                self.response.set_status(400)
                                                break
                                            else:
                                                newStock = Stock(ticker = value["ticker"], amount = value["amount"])
                                                portfolioObj.stock_portfolio.append(newStock)
                                    #Object is a List of Stocks
                                    elif (isinstance(value, types.ListType)):
                                        #Iterate Through Each Object in the List
                                        for element in value:
                                            Stock_Keys = list(element.keys())
                                            if (len(Stock_Keys) != 2 or all (elem in Stock_Keys for elem in stockElements) != True):
                                                break_flag = True
                                                self.response.set_status(400)
                                                break
                                            else:
                                                if (element["ticker"] not in validTickers or isinstance(element["amount"], types.IntType) != True):
                                                    break_flag = True
                                                    self.response.set_status(400)
                                                    break
                                                else:
                                                    newStock = Stock(ticker = element["ticker"], amount = element["amount"])
                                                    portfolioObj.stock_portfolio.append(newStock)
                                    elif (isinstance(value, types.NoneType)):
                                        break
                                    else:
                                        self.response.set_status(400)
                            if break_flag == False:
                                #Update Net Worth
                                portfolioObj.net_worth = getNetWorth(portfolioObj.stock_portfolio)
                                portfolioObj.put()
                                self.response.write(json.dumps(portfolioObj.to_dict()))
                                self.response.set_status(200)
                    else:
                        self.response.write("Portfolio Does Not Belong to User")
                        self.response.set_status(403)
            else:
                self.response.write("Unauthorized Access")
                self.response.set_status(403)
        else:
            self.response.write("User or Portfolio Does Not Exist")
            self.response.set_status(404)
    def get(self, userID, portfolioID):
        if checkUserID(userID) and checkPortfolioID(portfolioID):
            #Check Access Token
            headers = self.request.headers
            headerKeys = []
            for entity in headers:
                headerKeys.append(entity)
            if "Authorization" in headerKeys:
                Token = headers["Authorization"]
                if checkAccess(Token, userID):
                    #Check if Portfolio Taken
                    portfolioKey = ndb.Key(Portfolio, portfolioID)
                    portfolioObj = portfolioKey.get()
                    if portfolioObj.owner == userID:
                        #Update Net Worth
                        portfolioObj.net_worth = getNetWorth(portfolioObj.stock_portfolio)
                        portfolioObj.put()
                        self.response.write(json.dumps(portfolioObj.to_dict()))
                    else:
                        self.response.write("Portfolio Does Not Belong to User")
                        self.response.set_status(403)
            else:
                self.response.write("Unauthorized Access")
                self.response.set_status(403)
        else:
            self.response.write("User or Portfolio Does Not Exist")
            self.response.set_status(404)

class SpecificPortfolioHandler(webapp2.RequestHandler):
    def get(self, id):
        if checkPortfolioID(id):
            #Get Portfolio Object
            PortfolioObj = ndb.Key(Portfolio, id).get()
            #Check if Porfolio Belongs to an Owner
            if PortfolioObj.owner == None:
                self.response.write(json.dumps(PortfolioObj.to_dict()))
            else:
                headers = self.request.headers
                headerKeys = []
                ownerID = PortfolioObj.owner
                for entity in headers:
                    headerKeys.append(entity)
                if "Authorization" in headerKeys:
                    Token = headers["Authorization"]
                    if checkAccess(Token, ownerID):
                        self.response.write(json.dumps(PortfolioObj.to_dict()))
                    else:
                        self.response.write("Unauthorized Access")
                        self.response.set_status(403)
                else:
                    self.response.write("Unauthorized Access")
                    self.response.set_status(403)
        else:
            self.response.write("Portfolio Not Found")
            self.response.set_status(404)
    def delete(self, id):
        if checkPortfolioID(id):
            PortfolioKey = ndb.Key(Portfolio, id)
            PortfolioObj = PortfolioKey.get()
            if PortfolioObj.owner == None:
                PortfolioKey.delete()
                self.response.set_status(204)
            else:
                ownerID = PortfolioObj.owner
                headers = self.request.headers
                headerKeys = []
                for entity in headers:
                    headerKeys.append(entity)
                if "Authorization" in headerKeys:
                    Token = headers["Authorization"]
                    if checkAccess(Token, ownerID):
                        #Remove Portfolio From User Portfolio
                        ownerObj = ndb.Key(User, ownerID).get()
                        ownerObj.portfolio.remove(Portfolio.id)
                        ownerObj.put()
                        PortfolioKey.delete()
                        self.response.set_status(204)
                    else:
                        self.response.write("Unauthorized Access")
                        self.response.set_status(403)
                else:
                    self.response.write("Unauthorized Access")
                    self.response.set_status(403)
        else:
            self.response.write("Portfolio Not Found")
            self.response.set_status(404)
    def patch(self, id):
        if checkPortfolioID(id):
            portfolioObj = ndb.Key(Portfolio, id).get()
            if portfolioObj.owner == None:
                portfolioData = json.loads(self.request.body)
                portfolioKeys = list(portfolioData.keys())
                portfolioElements = ["name", "stock_portfolio"]
                break_flag = False
                if (len(portfolioKeys) > 2 or all(elem in portfolioElements for elem in portfolioData) != True):
                    print("Error with Keys")
                    break_flag = True
                    self.response.set_status(400)
                else:
                    validTickers = getValidTicker()
                    stockElements = ["ticker", "amount"]
                    for key, value in portfolioData.iteritems():
                        if (key == "name"):
                            if(isinstance(value, types.UnicodeType)):
                                portfolioObj.name = value
                            else:
                                break_flag = True
                                print("Error with Name Type")
                                self.response.set_status(400)
                                break
                        if (key == "stock_portfolio"):
                            #Empty Out Old Portfolio Object
                            del portfolioObj.stock_portfolio[:]
                            #Only One Object Since it is a Dictionary
                            if(isinstance(value, types.DictType)):
                                Stock_Keys = list(value.keys())
                                #Check that Dictionary has the Correct Elements
                                if (len(Stock_Keys) != 2 or all(elem in value for elem in stockElements) != True):
                                    break_flag = True
                                    self.response.set_status(400)
                                    break
                                else:
                                    if (value["ticker"] not in validTickers or isinstance(value["amount"], types.IntType) != True):
                                        break_flag = True
                                        self.response.set_status(400)
                                        break
                                    else:
                                        newStock = Stock(
                                        ticker=value["ticker"], amount=value["amount"])
                                        portfolioObj.stock_portfolio.append(newStock)
                                    #Object is a List of Stocks
                            elif (isinstance(value, types.ListType)):
                                #Iterate Through Each Object in the List
                                for element in value:
                                    Stock_Keys = list(element.keys())
                                    if (len(Stock_Keys) != 2 or all(elem in Stock_Keys for elem in stockElements) != True):
                                        break_flag = True
                                        self.response.set_status(400)
                                        break
                                    else:
                                        if (element["ticker"] not in validTickers or isinstance(element["amount"], types.IntType) != True):
                                            break_flag = True
                                            self.response.set_status(400)
                                            break
                                        else:
                                            newStock = Stock(ticker=element["ticker"], amount=element["amount"])
                                            portfolioObj.stock_portfolio.append(newStock)
                            elif (isinstance(value, types.NoneType)):
                                break
                            else:
                                self.response.set_status(400)
                if break_flag == False:
                    #Update Net Worth
                    portfolioObj.net_worth = getNetWorth(portfolioObj.stock_portfolio)
                    portfolioObj.put()
                    self.response.write(
                    json.dumps(portfolioObj.to_dict()))
                    self.response.set_status(200)
            else:
                headers = self.request.headers
                headerKeys = []
                ownerID = portfolioObj.owner
                for entity in headers:
                    headerKeys.append(entity)
                if "Authorization" in headerKeys:
                    Token = headers["Authorization"]
                    if checkAccess(Token, ownerID):
                        portfolioData = json.loads(self.request.body)
                        portfolioKeys = list(portfolioData.keys())
                        portfolioElements = ["name", "stock_portfolio"]
                        break_flag = False
                        if (len(portfolioKeys) > 2 or all(elem in portfolioElements for elem in portfolioData) != True):
                            print("Error with Keys")
                            break_flag = True
                            self.response.set_status(400)
                        else:
                            validTickers = getValidTicker()
                            stockElements = ["ticker", "amount"]
                            for key, value in portfolioData.iteritems():
                                if (key == "name"):
                                    if(isinstance(value, types.UnicodeType)):
                                        portfolioObj.name = value
                                    else:
                                        break_flag = True
                                        print("Error with Name Type")
                                        self.response.set_status(400)
                                        break
                                if (key == "stock_portfolio"):
                                    #Empty Out Old Portfolio Object
                                    del portfolioObj.stock_portfolio[:]
                                    #Only One Object Since it is a Dictionary
                                    if(isinstance(value, types.DictType)):
                                        Stock_Keys = list(value.keys())
                                        #Check that Dictionary has the Correct Elements
                                        if (len(Stock_Keys) != 2 or all(elem in value for elem in stockElements) != True):
                                            break_flag = True
                                            self.response.set_status(400)
                                            break
                                        else:
                                            if (value["ticker"] not in validTickers or isinstance(value["amount"], types.IntType) != True):
                                                break_flag = True
                                                self.response.set_status(400)
                                                break
                                            else:
                                                newStock = Stock(
                                                ticker=value["ticker"], amount=value["amount"])
                                                portfolioObj.stock_portfolio.append(newStock)
                                            #Object is a List of Stocks
                                    elif (isinstance(value, types.ListType)):
                                        #Iterate Through Each Object in the List
                                        for element in value:
                                            Stock_Keys = list(element.keys())
                                            if (len(Stock_Keys) != 2 or all(elem in Stock_Keys for elem in stockElements) != True):
                                                break_flag = True
                                                self.response.set_status(400)
                                                break
                                            else:
                                                if (element["ticker"] not in validTickers or isinstance(element["amount"], types.IntType) != True):
                                                    break_flag = True
                                                    self.response.set_status(400)
                                                    break
                                                else:
                                                    newStock = Stock(ticker=element["ticker"], amount=element["amount"])
                                                    portfolioObj.stock_portfolio.append(newStock)
                                    elif (isinstance(value, types.NoneType)):
                                        break
                                    else:
                                        self.response.set_status(400)
                        if break_flag == False:
                            #Update Net Worth
                            portfolioObj.net_worth = getNetWorth(portfolioObj.stock_portfolio)
                            portfolioObj.put()
                            self.response.write(
                            json.dumps(portfolioObj.to_dict()))
                            self.response.set_status(200)
                    else:
                        self.response.write("Unauthorized Access")
                        self.response.set_status(403)
                else:
                    self.response.write("Unauthorized Access")
                    self.response.set_status(403)
        else:
            self.response.write("Portfolio Not Found")
            self.response.set_status(404)

class clearDBHandler(webapp2.RequestHandler):
    def get(self):
        #Get List of Portfolio Objects
        PortfolioQuery = Portfolio.query()
        for portfolio in PortfolioQuery:
            PortfolioKey = ndb.Key(Portfolio, portfolio.id)
            PortfolioKey.delete()
        UserQuery = User.query()
        for user in UserQuery:
            UserKey = ndb.Key(User, user.id)
            UserKey.delete()
        self.response.write("Everything was deleted")


app = webapp2.WSGIApplication([
    ('/', MainPageHandler),
    ('/oAuth', OAuthHandler),
    ('/user', UserHandler),
    ('/user/(\w{5})', SpecificUserHandler),
    ('/portfolio', PortfolioHandler),
    ('/user/(.*)/portfolio/(.*)', UserPortfolioHandler),
    ('/portfolio/(.*)', SpecificPortfolioHandler),
    ('/clearDB', clearDBHandler)
], debug=True)
