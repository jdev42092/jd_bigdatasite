import jsonpickle
import tweepy
import pandas as pd
import requests
import bs4
import numpy as np
import matplotlib.pyplot as plt
%matplotlib inline


# Imports twitter keys
import os
os.chdir('/Users/jaydev/Desktop/DUSP/11.S941/big-data-spring2018/week-04')
from twitter_keys import api_key, api_secret
os.chdir('/Users/jaydev/Dropbox (MIT)/BDVS Team Folder/twitter files/')

# Set up tweepy scraper with authentication
def auth(key, secret):
  auth = tweepy.AppAuthHandler(key, secret)
  api = tweepy.API(auth, wait_on_rate_limit = True, wait_on_rate_limit_notify = True)
  # Print error and exit if there is an authentication error
  if (not api):
      print ("Can't Authenticate")
      sys.exit(-1)
  else:
      return api

api = auth(api_key, api_secret)

# Create scraper and parser
def get_users(
    user_list,
    id_list,
    out_file,
    write = False
    ):
    all_users = pd.DataFrame()
    i = 0
    for user in user_list:
        try:
            new_user = api.get_user(screen_name = user)
            #print(new_user)
            all_users = all_users.append(parse_user(new_user), ignore_index = True)
            #print(all_users)
            if write == True:
                with open(out_file, 'w') as f:
                    f.write(jsonpickle.encode(new_user._json, unpicklable=False) + '\n')
        except tweepy.TweepError as e:
          try:
              # Try using user_id
              new_user = api.get_user(user_id = id_list[i])
              all_users = all_users.append(parse_user(new_user), ignore_index = True)
              if write == True:
                  with open(out_file, 'w') as f:
                      f.write(jsonpickle.encode(new_user._json, unpicklable=False) + '\n')
          except tweepy.TweepError as e:
              continue
        i += 1

    return all_users

def parse_user(user):
    p = pd.Series()
    p['id'] = user.id_str
    p['user'] = user.screen_name
    p['location'] = user.location
    p['profile'] = user.description
    p['followers'] = user.followers_count
    p['friends'] = user.friends_count
    p['verified'] = user.verified
    return p

## Replace common typos
def fix_typos(df):
    df['target'] = df['target'].str.lower()
    df['target'].replace('bostinn','bostinno', inplace=True)
    df['target'].replace('bostinnoo','bostinno', inplace=True)
    df['target'].replace('bostonglob','bostonglobe', inplace=True)
    df['target'].replace('bostonglobee','bostonglobe', inplace=True)
    df['target'].replace('fox25news','boston25', inplace=True)
    df['target'].replace('mashabl','mashable', inplace=True)
    df['target'].replace('mashablee','mashable', inplace=True)
    df['target'].replace('nwsbosto','nwsboston', inplace=True)
    df['target'].replace('nwsbostonn','nwsboston', inplace=True)
    df['target'].replace('pbouchardon7','petenbcboston', inplace=True)
    df['target'].replace('youtub','youtube', inplace=True)
    df['target'].replace('youtubee','youtube', inplace=True)
    df['target'].replace('weatherchanne','weatherchannel', inplace=True)
    df['target'].replace('weatherchannell','weatherchannel', inplace=True)
    df['target'].replace('nationalgri','nationalgrid', inplace=True)
    df['target'].replace('nationalgridd','nationalgrid', inplace=True)
    return df

# Read user ids from all storm files
def extract_users (df, min_tweets = 20):
    df.drop_duplicates('ID', inplace = True)
    ## Count Users
    df['usernameTweet'] = df['usernameTweet'].str.lower()
    user_counts = pd.DataFrame(df['usernameTweet'].value_counts())
    user_counts.columns = ['count']
    ## Extract and count mentions
    mentions = expand_mentions(df)
    mention_counts = pd.DataFrame(mentions['target'].value_counts())
    mention_counts.columns = ['n_mentions']

    ## Combine users and mentions
    all_users = user_counts.merge(mention_counts, how="outer", left_index=True, right_index=True)
    all_users['count'].fillna(0, inplace = True)
    all_users['n_mentions'].fillna(0, inplace = True)
    all_users['total_tweets'] = all_users['count'] + all_users['n_mentions']
    all_users.sort_values('total_tweets', inplace = True, ascending = False)

    ## Merge user IDs
    all_user_ids = df[['usernameTweet', 'user_id']]
    all_user_ids.drop_duplicates('user_id', inplace = True)
    all_user_ids.set_index('usernameTweet', inplace = True)

    user_counts_cut = all_users[all_users['total_tweets'] >= min_tweets]
    user_counts_cut_ids = pd.merge(left = user_counts_cut, right = all_user_ids, how = "left", left_index = True, right_index = True)
    user_names = user_counts_cut.index.values
    user_ids = user_counts_cut_ids.user_id.values
    print("Number of unique usernames: ", user_counts_cut.shape[0])
    print("Number of unique user_ids: ", user_counts_cut_ids.user_id.notnull().sum())
    return user_counts_cut, user_names, user_ids, mentions

def find_mentions(tweet_df):
    tweet_df['mentions'] = tweet_df['text'].str.count('@')

    mentions = []

    for index, row in tweet_df.iterrows():
        i = 0
        text_to_parse = row['text']
        begin_parse = 0
        while i < row['mentions']:
            begin_parse = text_to_parse.find('@', begin_parse)
            end_parse = text_to_parse.find(' ',begin_parse + 2)
            if end_parse == -1:
                end_parse = len(text_to_parse)
            user = text_to_parse[begin_parse:end_parse]
            user = user.replace(" ","")
            user = user.replace(":","")
            user = user.replace(".","")
            user = user.replace("?","")
            user = user.replace("!","")
            user = user.replace("@","")
            #print(user)
            mentions.append(user)
            i += 1
    mention_names = pd.DataFrame(mentions, columns=['username'])
    mention_names['username'].value_counts()
    return mentions

def expand_mentions(tweet_df):
    tweet_df['mentions'] = tweet_df['text'].str.count('@')
    tweet_df['target']=''
    new_rows = []

    for index, row in tweet_df.iterrows():
        i = 0
        text_to_parse = row['text']
        begin_parse = 0
        while i < row['mentions']:
            begin_parse = text_to_parse.find('@', begin_parse)
            end_parse = text_to_parse.find(' ',begin_parse + 2)
            if end_parse == -1:
                end_parse = len(text_to_parse)
            user = text_to_parse[begin_parse:end_parse]
            user = user.replace(" ","")
            user = user.replace(":","")
            user = user.replace(".","")
            user = user.replace("?","")
            user = user.replace("!","")
            user = user.replace("@","")
            #print(user)
            dup_row = row
            dup_row['target'] = user
            new_rows.append(dup_row.values)
            i += 1
    tweet_df = tweet_df.append(pd.DataFrame(new_rows, columns = tweet_df.columns)).reset_index()
    tweet_df = tweet_df[tweet_df['target'] != '']
    tweet_df = fix_typos(tweet_df)
    return tweet_df




# sample_ids = extract_users("TweetScraper-master/Data/bombcyclone/tweets_bombcyclone boston.csv")
# Read in tweets, scraped and cleaned by Sarah and Jay
nemo_tweets = pd.read_csv("cleaned data by storm/nemo_tweets.csv", encoding = "ISO-8859-1")
juno_tweets = pd.read_csv("cleaned data by storm/juno_tweets.csv", encoding = "ISO-8859-1")
bombo_tweets = pd.read_csv("cleaned data by storm/bombo_tweets.csv", encoding = "ISO-8859-1")
skylar_tweets = pd.read_csv("cleaned data by storm/skylar_tweets.csv", encoding = "ISO-8859-1")
allstorms_tweets = pd.concat([nemo_tweets, juno_tweets, bombo_tweets, skylar_tweets])

nemo_mentions = expand_mentions(nemo_tweets)
juno_mentions = expand_mentions(juno_tweets)
bombo_mentions = expand_mentions(bombo_tweets)
skylar_mentions = expand_mentions(skylar_tweets)
allstorms_mentions = pd.concat([nemo_mentions,juno_mentions,bombo_mentions,skylar_mentions])

# Extract top users from each storm, and overall
nemo_users, nemo_list, nemo_ids, nemo_convos = extract_users(nemo_tweets, 50)
juno_users, juno_list, juno_ids, juno_convos = extract_users(juno_tweets, 50)
bombo_users, bombo_list, bombo_ids, bombo_convos = extract_users(bombo_tweets, 50)
skylar_users, skylar_list, skylar_ids, skylar_convos = extract_users(skylar_tweets, 50)
allstorms_users, allstorms_list, allstorms_ids, allstorms_convos = extract_users(allstorms_tweets, 50)


## Pull data on twitter users using API
user_names = allstorms_list
user_ids = allstorms_ids
file_name = 'UserData/allstorms_user.json'

allstorms_user_data = get_users(
    user_list = user_names,
    id_list = user_ids,
    out_file =  file_name,
    write = False)
## Merge user data to tweet activity
def merge_by_users(activity_df, user_data_df):
    user_data_df['user'] = user_data_df['user'].str.lower()
    user_data_df.set_index('user', inplace = True)
    activity_df.reset_index(inplace = True)
    activity_df['index'] = allstorms_users['index'].str.lower()
    activity_df.set_index('index', inplace = True)

    merged_df =  pd.merge(left = activity_df, right = user_data_df, how="left", left_index = True, right_index = True)
    return merged_df

allstorms_merged = merge_by_users(activity_df=allstorms_users, user_data_df=allstorms_user_data)


allstorms_merged.reset_index(inplace = True)
allstorms_merged.to_json(file_name)
allstorms_merged.to_csv('UserData/allstorms_user.csv')
allstorms_from_json = pd.read_json(file_name)
allstorms_tweets.shape
## Users are categorized externally using excel
## Aggregate data sets by nodes and targets
all_node_data = pd.read_csv('UserData/allstorms_user_categorized.csv')
node_data=all_node_data[['index','group','size']]
node_data = node_data.rename(index = str, columns = {'index':'id'})
node_data

def create_links(df_convos):
    df_convos_cleaned = df_convos.rename(index = str, columns = {'usernameTweet':'source'})
    df_convos_cleaned.drop_duplicates(subset = ['source','target','ID'],inplace = True)
    links = df_convos_cleaned[['source','target','ID']].groupby(['source','target'], as_index = False).count()
    links = links[links['source'] != links['target']]
    return links


all_convos = create_links(allstorms_convos)
main_convos = all_convos.merge(pd.DataFrame(node_data['id']),left_on = 'source', right_on = 'id', how = "inner")
main_convos = main_convos.merge(pd.DataFrame(node_data['id']),left_on = 'target', right_on = 'id', how = "inner")
main_convos = main_convos[['source','target','ID']]

main_nodes = node_data.merge(pd.DataFrame(main_convos['source']),left_on = 'id', right_on='source', how='left')
main_nodes = main_nodes.merge(pd.DataFrame(main_convos['target']),left_on = 'id', right_on='target', how='left')
main_nodes = main_nodes[(main_nodes['source'].notnull()) | (main_nodes['target'].notnull())]
main_nodes = main_nodes[['id','group','size']].drop_duplicates('id')


main_convos_try = main_convos[['source','target']].apply(sorted,1)
links = main_convos.groupby([main_convos_try['source'],main_convos_try['target']])['ID'].sum().reset_index(name = "ID")

links = links.rename(index=str,columns={"ID":"value"})
main_nodes.to_json('UserData/allstorms_nodes.json', orient='records')
links.to_json('UserData/allstorms_links.json', orient='records')
# To do:
##  - Change location, profile, user to string
###     df['column'] = df['column'].astype('str')
##  - Append storm data together, separate into lists of 100 users
##  - Build-in pause after 100 users?
