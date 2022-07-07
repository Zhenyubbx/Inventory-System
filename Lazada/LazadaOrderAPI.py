from math import prod
from lazop_sdk import LazopClient, LazopRequest
import sys
import os
# setting path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
import config_tools_lazada as config_tools
import pandas as pd
from LazadaAuthorisation import Authorisation
from requests.exceptions import ConnectionError

import sys
import os
# setting path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
from functions import convert_ISO, generate_qty_table


#Get new access token
def get_new_access_token():
    access_token, refresh_token = config_tools.read_token_config()
    if (len(refresh_token) == 0):
        auth_url = Authorisation().concatenate_authorization_url()
        print(f"Please get code from authorization using the URL:\n{auth_url}")
        
        CODE = "0_110194_P5OR9Z4G8j6ap5IoGCihVWsB44280"
        access_token, refresh_token = Authorisation().get_access_token(CODE)
    else:
        access_token, refresh_token = Authorisation().refresh_access_token(refresh_token)
    config_tools.write_token_config(access_token, refresh_token)
    print("refresh token: " + refresh_token)
    print ("access_token: " + access_token)
    print("\n")
    return access_token

#Get orders and their ID
#'2021-01-01T00:00:00+08:00'--> #No orders before this date
def get_order_list(last_created_after):
    access_token = get_new_access_token()
    
    url = f"https://api.lazada.sg/rest"
    app_key, app_secret = config_tools.read_credentials_config()

    orders=pd.DataFrame()
    # last_created_after = '2021-01-01T00:00:00+08:00' #No orders before this date
    is_first_loop = True
    while True:
        client = LazopClient(url, app_key ,app_secret)
        request = LazopRequest('/orders/get','GET')
        request.add_api_param('created_after', last_created_after) 
        request.add_api_param('limit', '100') #100 is the maximum number of orders per GET request
        try:
            response = client.execute(request, access_token)
            print(response.body)
            if len(response.body['data']['orders']) != 0: #If there are new orders since last_created_after
                if is_first_loop:  #Starts with first row
                    df = pd.DataFrame([response.body['data']['orders'][0]])
                    for i in range(len(response.body['data']['orders']) - 1):
                        temp_df = pd.DataFrame([response.body['data']['orders'][i + 1]])
                        df = pd.concat([df, temp_df]) #For the particular loop of GET request
                    orders = pd.concat([orders, df])

                    # print("First loop: " + str(len(df)))
                    if len(df)<100:
                        break
                    
                else: #Starts with second row because first row is duplicate of previous loop dataframe because of variable "last_created_after"
                    df = pd.DataFrame([response.body['data']['orders'][1]])
                    for i in range(len(response.body['data']['orders']) - 2):
                        temp_df = pd.DataFrame([response.body['data']['orders'][i + 2]])
                        df = pd.concat([df, temp_df]) #For the particular loop of GET request
                    orders = pd.concat([orders, df])
                    
                    # print("Not First loop: " + str(len(df)))
                    if len(df)<99:
                        break 
                    
                last_created_after = convert_ISO(df['created_at'].iloc[-1])
                is_first_loop = False
            else:
                df = pd.DataFrame()
                orders = pd.DataFrame()
        except ConnectionError as connection_error:
            print(connection_error)
            orders = pd.DataFrame()

    return orders, access_token

#Get order details
def get_order_details(order_id, access_token):
    # access_token = get_new_access_token()

    url = f"https://api.lazada.sg/rest"
    app_key, app_secret = config_tools.read_credentials_config()

    client = LazopClient(url, app_key ,app_secret)
    request = LazopRequest('/order/items/get','GET')
    request.add_api_param('order_id', order_id) 
    try: 
        response = client.execute(request, access_token)
        df = pd.DataFrame(response.body['data'])
        product_dict = {}
        for product in df["name"]:
            if product not in product_dict.keys():
                product_dict[product] = 1
            else:
                product_dict[product] += 1
        df = df.drop_duplicates(subset=['order_id'])
        df["name"] = pd.Series([str(product_dict)])
    except ConnectionError as connection_error:
        print(connection_error)
        df = pd.DataFrame()
    return df

#Get order more detail, like address, remark
def get_order_details2(order_id, access_token):
    # access_token = get_new_access_token()

    url = f"https://api.lazada.sg/rest"
    app_key, app_secret = config_tools.read_credentials_config()

    client = LazopClient(url, app_key ,app_secret)
    request = LazopRequest('/order/get','GET')
    request.add_api_param('order_id', order_id) 
    try:
        response = client.execute(request, access_token)
        df = pd.DataFrame(response.body['data']['address_billing'], index=[0])
        df['address'] = df['address1'] + " " + df['post_code']
        df['Notes'] = response.body['data']['remarks']
        df['order_id'] = order_id
    except ConnectionError as connection_error:
        print(connection_error)
        df = pd.DataFrame()
    return df

#Cleans data in the dataframe
def clean_df(df):
  
    df = df[['order_id', 'created_at',  'status', 'Notes', 'paid_price', 'currency', 'name' , 'phone', 'address', 'first_name']] # keep needed columns

    df = df.rename(columns={"order_id":"Order No.", "created_at":"Created At","status":"Fulfillment Status", "remark":"Notes",  #Renames columns
    "phone":"HP", "address":"Address", "first_name":"Name", "paid_price":"Amount Spent", "currency":"Currency","name":"Product" })

    # df["Product"] = "{'" + df["Product"].values + "':1}"
    df["Platform"] = "Lazada"

    df = df.reset_index(drop=True)

    return df

#Splits one column into individual columns
def split_column(df, column_header):
    new_df = pd.DataFrame()
    for dictItr in df[column_header]: #split item_list into individual columns
        temp_df = pd.DataFrame.from_dict([dictItr])
        new_df = pd.concat([temp_df,new_df])
    return new_df

#Generate full order df
def generate_full_order_df(default_qty_df):
    df = get_all_orders()
    df = clean_df(df)
    df, unmatchedProducts = generate_qty_table(df, default_qty_df, "Lazada")
    return df, unmatchedProducts

def get_all_orders(last_created_after = '2021-01-01T00:00:00+08:00'): 
    order_list_df, access_token = get_order_list(last_created_after)
    if len(order_list_df) != 0: #If there are new orders since last_created_after
        df = pd.DataFrame() #empty dataframe
        #loops through every order id in order list dataframe and gets order detail
        for order_id in order_list_df["order_id"]:
            order_df = get_order_details(order_id, access_token)
            order_df2 = get_order_details2(order_id, access_token)
            if len(order_df) != 0 and len(order_df2) != 0: #If connection error occur in get order details and get order detials2
                order_df = pd.merge(order_df, order_df2, on='order_id', how='left')
                df = pd.concat([df,order_df])
        return df
    else:
        return order_list_df

#Remove customer data from cleaned data
def clean_wo_customer_data(old_df, new_df):
    #check old df is correct, use left join instead
    new_df = new_df.reset_index(drop=True)
    old_df = old_df.reset_index(drop=True)
    new_df.drop(['HP', 'Address', 'Name'], axis=1, inplace=True)
    new_df = new_df.merge(old_df[['Order No.', 'HP', 'Address', 'Name']], how="left", on="Order No.")
    new_df = new_df.reset_index(drop=True)
    
    return new_df
    
#Returns a dataframe of orders since last input date
def generate_new_order_df(default_qty_df, update_date, old_df): #lastDate in IS08601 format
    new_df = get_all_orders(update_date)
    if len(new_df)!=0: #If there are new orders since last_date
        new_df = clean_df(new_df)
        if len(old_df) != 0: #If there are any orders from outdated database to update
            trimmed_df = new_df[new_df["Created At"] <= old_df["Created At"].iloc[-1]]
            new_df = clean_wo_customer_data(old_df, trimmed_df)
        df, unmatched_products = generate_qty_table(new_df, default_qty_df, "Lazada")
    else:
        df = new_df
        unmatched_products = pd.Series()
    return df, unmatched_products

# from functions import get_default_path, get_default_qty
# get_default_path()
# defaultQtyDf = get_default_qty()

# #For Lazada
# generate_full_order_df(defaultQtyDf)