from Shopify.ShopifyCustomerAPI import ShopifyCustomerAPI
import Shopify.ShopifyOrderAPI as ShopifyOrderAPI
import Shopee.ShopeeAPI as ShopeeAPI
import Lazada.LazadaOrderAPI as LazadaOrderAPI
from functions import get_default_path, get_default_qty, combine_orders_cust_df, combine_dfs
from functions import API_KEY, PASSWORD, HOSTNAME, VERSION

if __name__ == "__main__":
    
    #Gets path setting
    CUSTOMER_DATA, COMBINED_DATA = get_default_path()
    
    # Gets customers database
    print("Getting customers from Shopify...")
    ShopifyFullCustDf = ShopifyCustomerAPI(API_KEY, PASSWORD, HOSTNAME, VERSION).generate_full_cust_df()
    # ShopifyFullCustDf = pd.read_excel(CUSTOMER_DATA)
    ShopifyFullCustDf.to_excel(CUSTOMER_DATA, index=False)

    #Gets orders database
    defaultQtyDf = get_default_qty()
    #For Shopify
    print("Getting orders from Shopify...")
    ShopifyFullOrderDf, unmatchedProducts = ShopifyOrderAPI.generate_full_order_df(defaultQtyDf)
    #For Shopee
    print("Getting orders from Shopee...")
    ShopeeFullOrderDf, unmatchedProducts = ShopeeAPI.generate_full_order_df(defaultQtyDf)
    #For Lazada
    print("Getting orders from Lazada...")
    LazadaFullOrderDf, unmatchedProducts = LazadaOrderAPI.generate_full_order_df(defaultQtyDf)
    
    #Combines Customer and Order Df
    shopifyCombined = combine_orders_cust_df(ShopifyFullCustDf, ShopifyFullOrderDf)
    
    #Combines platforms
    combinedDf = combine_dfs(shopifyCombined, ShopeeFullOrderDf, LazadaFullOrderDf)
    combinedDf.to_excel(COMBINED_DATA, index=False)
