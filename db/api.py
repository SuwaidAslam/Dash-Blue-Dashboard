from traceback import print_tb
import pandas as pd
import psycopg2
import os
from sqlalchemy import create_engine
from urllib.parse import quote_plus as urlquote
from decouple import config



DATABASE = os.environ['DATABASE']
USER = os.environ['USER']
PASSWORD = os.environ['PASSWORD']
HOST = os.environ['HOST']
PORT = os.environ['DB_PORT']

CONN = f"postgresql+psycopg2://{USER}:%s@{HOST}:{PORT}/{DATABASE}" % urlquote(PASSWORD)

def get_latest_df():
    """
    Helper function to filter latest data by date and hour

    :returns: pandas dataframe object
    """
    engine = create_engine(CONN)
    # query_ = '''SELECT *, Date(datetime) As date, extract(hour from datetime) as hour FROM npg_sgx_sbl_prd''' 
    query_ = '''SELECT *, Date(datetime) As date, extract(hour from datetime) as hour
    From npg_sgx_sbl_prd Where Date(datetime) = (select DATE(datetime) as date from npg_sgx_sbl_prd ORDER BY date DESC LIMIT 1)
    AND extract(hour from datetime) = (select extract(hour from datetime) as hour from npg_sgx_sbl_prd ORDER BY hour DESC LIMIT 1)'''
    latest_hour_df = pd.read_sql(query_, engine)

    # just in case we need it :)
    # df = pd.read_sql(query_, engine)
    # grouped = df.groupby('date')
    # groups = []
    # for name,group in grouped:
    #     groups.append(group)
    # latest_group = groups[-1]
    # grouped_byhour = latest_group.groupby('hour')
    # hour_groups = []
    # for name, group in grouped_byhour:
    #     hour_groups.append(group)
    # latest_hour_df = hour_groups[-1]
    latest_hour_df['borrowed'] = latest_hour_df['lending_pool'].diff()
    latest_hour_df.drop(['date', 'hour'], axis=1, inplace=True)
    return latest_hour_df

def get_top_smallest_data(latest_hour_df):
    """
    Query top 15 latest negative values

    :returns: pandas dataframe object
    """
    top_negative_df = latest_hour_df.nsmallest(15,"borrowed")  # The negative
    return top_negative_df

def get_top_largest_data(latest_hour_df):
    """
    Query top 15 latest positive values

    :returns: pandas dataframe object
    """
    top_positive_df = latest_hour_df.nlargest(15,"borrowed")  # The Positive
    return top_positive_df


def get_filtered_data(security_name):
    """
    Query 141 records based on security name

    :params security_name: filter the data by security name
    :returns: pandas dataframe object
    """
    engine = create_engine(CONN)
    query_ = f'''SELECT * FROM npg_sgx_sbl_prd Where security_name = '{security_name}' LIMIT 141;'''
    df = pd.read_sql(query_, engine)
    df = df.sort_values(by=['security_name', 'datetime'])
    df['borrowed'] = df['lending_pool'].diff()
    df.sort_values(by='datetime', ascending=False, inplace=True)
    return df

def get_unique_security_names_list():
    """
    Query all unique security names and convert them to a list

    :returns: a list
    """
    engine = create_engine(CONN)
    query_ = '''SELECT DISTINCT security_name FROM npg_sgx_sbl_prd'''
    df = pd.read_sql(query_, engine)
    return df['security_name'].tolist()
