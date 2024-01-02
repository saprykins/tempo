import html2text
import requests
import base64
import pandas as pd
import time

pat = 'l*'
organization = 'g*'
project = 'M*'

authorization = str(base64.b64encode(bytes(':'+pat, 'ascii')), 'ascii')


# initialization dataFrame
cols_app =  [
    "App id in ADO", 
    "App name", 
    "Environment",
    "State", 
    "Entity",
    "Planned migration date",
    "Actual migration startdate",
    "Actual migration enddate",
    "Data center",
    "Blocker details",
    "De-scoping Details",
    "Flow opening confirmation", # not available
    "Last minute reschedule",
    "Migration eligibility",
    "Planned Wave", # not available
    "Internet  access through proxies",
    "Outbound Emails",
    "Reverse Proxies",
    "WAC",
    "WAF",
    "VPN",
    "Load Balancer",
    "Service Account in local AD domains",
    "Encryption",
    "Secret data",
    "Fileshare",
    "Administration through specific Jump servers",
    "Access through specific Citrix Jump servers",
    "Out of business hours",
    "Zero downtime requirements",
    "Risk level",
    "Factory",
    "Sign-off DBA", # NOK
    "Sign-off Entity", # NOK
    "Schedule_change_Description"
    ]

cols_servers = ["Server id in ADO", "Server", "FQDN", "Sign-off Ops", "Sign-off DBA"]
cols_map_servers_apps = ["Server id in ADO", "App id in ADO"]

df_applications = pd.DataFrame([],  columns = cols_app)
df_servers = pd.DataFrame([],  columns = cols_servers)
df_map_server_vs_app = pd.DataFrame([],  columns = cols_map_servers_apps)



def get_mig_date(playbook_id):
    try:
        date = df_dates.loc[df_dates["Playbook WI"] == playbook_id, "Mig date"]
    # print(date[0])
    except:
        date = ""
    return date




def get_app_list_for_the_wave(list_of_applications):
    """
    Contains 2 parts: wave2 and entity AFA
    """

    # part 2 (getting microsoft apps)
    url = "https://dev.azure.com/" + organization + "/" + project + "/_apis/wit/wiql/bf60899f-afe1-4701-b5e3-fcd4ae04dd31" # all in ms projects
    # url = "https://dev.azure.com/" + organization + "/" + project + "/_apis/wit/wiql/0ff32d40-394e-45fe-a593-31d8ada166e9" # template only
    
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic '+ authorization
    }
    response = requests.get(
        url = url,
        headers=headers,
    )

    list_of_all_ms_applications = [] # 
    applications_raw_data = response.json()["workItems"]
    for application in applications_raw_data:
        list_of_all_ms_applications.append(application["id"])

    
    return list_of_all_ms_applications




def save_application_wi_into_data_frame(application_wi_id, df_applications):   
    """
    Get a working item title, parent, status 
    and saves it into a dataframe
    application_wi_id - the application for which data is extracted
    df_applications - used as storage object
    """
    
    url = 'https://dev.azure.com/' + organization + '/_apis/wit/workItems/' + str(application_wi_id) + '?$expand=all'
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic '+ authorization
    }
    response = requests.get(
        url = url,
        headers=headers,
    )

    # list of app attributes
    # is used to use cycles
    app_attributes = []

    # list of keys in ADO
    app_keys_ado = [
        "System.Title", 
        "Custom.EnvironmentTargetSubscription",
        "System.State",
        "Custom.Entity",
        "Custom.PlannedStartDate", # planned cut-over date
        "Custom.MigrationStartDate",
        "Custom.MigrationEndDate", # new field
        "Custom.DataCenter",
        "Custom.RollbackReason", # de-scoping or blocker detail -> rollback reason
        "Custom.DeScopingDetails" # should go deeper
        "Custom.DeScopingDetails", # should go deeper
        "Custom.Status2", # FW OK
        "Custom.LastMinuteReschedule", # last minute reschedule
        "Custom.MigrationEligibility", # ok
        "Custom.Wave", # not available
        "Custom.Internetaccessthroughproxies",
        "Custom.OutboundEmails", # ok
        "Custom.ReverseProxies",
        "Custom.WAC",
        "Custom.WAF",
        "Custom.VPN",
        "Custom.LoadBalancer",
        "Custom.ServiceAccountinlocalADdomains",
        "Custom.Encryption",
        "Custom.SecretData",
        "Custom.FileShare",
        "Custom.AdminJumpServer",
        "Custom.AccessthroughspecificCitrixJumpservers",
        "Custom.MigrationConstraint",
        "Custom.ZeroDownTime",
        "Custom.RiskLevel", 
        "Custom.ApplicationOwnershipOrganization",
        "Sign-off DBA",
        "Sign-off Entity",
        "System.Description"
    ]

    # Try to get data from ADO using keys, 
    # if key not found, save empty space
    for i in range(len(app_keys_ado)):
        try:
            app_attributes.insert(i+1, response.json()["fields"][app_keys_ado[i]])  # may be need to string
        except: 
            app_attributes.insert(i+1, "")

    
    # app_attributes[0] = application_wi_id
    app_attributes.insert(0, application_wi_id)

    # getting date from AFA Reports
    app_attributes[-4] = "Microsoft"

    # default description 
    default_description_1 = "Add Application all"
    default_description_2 = "Add short description"

    # line with html code that requires text treatment: 
    try:
        description = response.json()["fields"]["System.Description"]
        description = html2text.html2text(description)
        if (((description.startswith(default_description_1)) | (description.startswith(default_description_2)))):
        # if (description.startswith("Add short description")):
            description = ""
            app_attributes[-1] = description
        else:
            app_attributes[-1] = html2text.html2text(description)
    except: 

        app_attributes[-1] = ""


    new_row = app_attributes
    new_df = pd.DataFrame([new_row], columns=cols_app)
    
    # load data into a DataFrame object:
    df_applications = pd.concat([df_applications, new_df], ignore_index = True)

    return df_applications



def get_server_wi_ids_from_feature(feature_id):
    """
    Given feature_id the function gets data on its children
    It verified if feature name is "Servers"
    And get its children ids
    """

    url = 'https://dev.azure.com/' + organization + '/_apis/wit/workItems/' + str(feature_id) + '?$expand=all'
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic '+ authorization
    }

    response = requests.get(
        url = url,
        headers=headers,
    )
    
    list_of_ids_of_servers = []

    feature_title = response.json()["fields"]["System.Title"]
    if feature_title == "Servers":
        relations = response.json()["relations"]
        for relation in relations: 
            if relation["rel"] == "System.LinkTypes.Hierarchy-Forward":
                raw_id = relation['url']
                start_line = raw_id.find('workItems/') + 10
                server_id = int(raw_id[start_line:])
                list_of_ids_of_servers.append(server_id)

    return list_of_ids_of_servers



def get_server_wi_ids_from_application(application_id):
    """
    Given app_id, this function gets ids of its servers
    """

    url = 'https://dev.azure.com/' + organization + '/_apis/wit/workItems/' + str(application_id) + '?$expand=all'
    servers_id = []
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic '+ authorization
    }
    response = requests.get(
        url = url,
        headers=headers,
    )
    
    # go through features of an app
    # not all applications have servers stored in ADO
    try:
        wi_relations = response.json()["relations"]
    except: 
        wi_relations = ""

    for relation in wi_relations:
        if relation["rel"] == "System.LinkTypes.Hierarchy-Forward":
            # need to go deeper to find servers
            # features can be servers or playbook
            raw_id = relation['url']
            start_line = raw_id.find('workItems/') + 10
            feature_id = int(raw_id[start_line:])
            # print(feature_id) # correct
            list_of_ids_of_servers = get_server_wi_ids_from_feature(feature_id)
            if len(list_of_ids_of_servers)>0:
                # print(list_of_ids_of_servers)
                servers_id = servers_id + list_of_ids_of_servers

        # should we keep it (only 1 feature with servers)
        elif relation["rel"] == "System.LinkTypes.Hierarchy-Reverse":
            # get wave name
            raw_id = relation['url']
            start_line = raw_id.find('workItems/') + 10
            parent_id = int(raw_id[start_line:])
            # print(parent_id)

        # print(relation)
    return servers_id



def save_server_wi_into_data_frame(server_wi_id, df_servers):
    """
    Get a server hostname, statuses
    and saves it into a dataframe
    """
    
    url = 'https://dev.azure.com/' + organization + '/_apis/wit/workItems/' + str(server_wi_id) + '?$expand=all'
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic '+ authorization
    }
    response = requests.get(
        url = url,
        headers=headers,
    )
    # server item Title
    wi_title = response.json()["fields"]["System.Title"]

    # server hostname
    try:
        wi_hostname = response.json()["fields"]["Custom.HostName"]
    except: 
        wi_hostname = ""

    # need insert sign-off state    


    sign_off_ops_state = ''
    sign_off_dba_state = ''
    # working item sign-offs DBA
    try:
        sign_off_ops_state = response.json()["fields"]["Custom.SignofffromOpsteam"]
    except: 
        sign_off_ops_state = ""
    
    try:
        sign_off_dba_state = response.json()["fields"]["Custom.SignofffromDBA"]
    except: 
        sign_off_dba_state = ""
    

    new_row = [server_wi_id, wi_title, wi_hostname, sign_off_ops_state, sign_off_dba_state]
    new_df = pd.DataFrame([new_row], columns=cols_servers)

    # load data into a DataFrame object:
    df_servers = pd.concat([df_servers, new_df], ignore_index = True)

    return df_servers


def get_all_servers_list_from_ado():
    """
    The function uses query that is defined in ADO
    The mentioned query displays the list of all servers
    """
    list_of_all_servers = []
    
    url = "https://dev.azure.com/" + organization + "/" + project + "/_apis/wit/wiql/fad91720-c6b5-4e92-be7a-9d98b41d6289" # servers
    # url = "https://dev.azure.com/" + organization + "/" + project + "/_apis/wit/wiql/acc34e05-21d5-4d12-8405-fd3206f371e1" # 2 servers only
    
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic '+ authorization
    }
    response = requests.get(
        url = url,
        headers=headers,
    )

    servers_raw_data = response.json()["workItems"]

    for server in servers_raw_data:
        list_of_all_servers.append(server["id"])
    return list_of_all_servers



def get_all_applications_list_from_ado():
    """
    The function uses query that is defined in ADO
    The mentioned query displays the list of all applications (for all waves in the projects)
    The function exists to create mapping between applications and servers
    """
    list_of_all_applications = []
    
    url = "https://dev.azure.com/" + organization + "/" + project + "/_apis/wit/wiql/e2c3101f-d2e2-4156-a57d-53b40a6fec6a"
    # url = "https://dev.azure.com/" + organization + "/" + project + "/_apis/wit/wiql/0ff32d40-394e-45fe-a593-31d8ada166e9" # only one app
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic '+ authorization
    }
    response = requests.get(
        url = url,
        headers=headers,
    )
    applications_raw_data = response.json()["workItems"]
    for application in applications_raw_data:
        list_of_all_applications.append(application["id"])
    return list_of_all_applications


def save_map_server_vs_app(application_wi_id, df_map_server_vs_app): 
    """
    Get a map between ids (servers vs applications)
    """
    
    list_of_servers = get_server_wi_ids_from_application(application_id)
    for server_id_ado in list_of_servers: 
        new_row = [server_id_ado, application_wi_id]
        new_df = pd.DataFrame([new_row], columns=cols_map_servers_apps)
        # load data into a DataFrame object:
        df_map_server_vs_app = pd.concat([df_map_server_vs_app, new_df], ignore_index = True)  
    return df_map_server_vs_app





# MAIN
start_time = time.time()/60 # sec

# global storage var
list_of_applications = []
list_of_applications = get_app_list_for_the_wave(list_of_applications)


# display the table with apps and details
for application_id in list_of_applications: 
    df_applications = save_application_wi_into_data_frame(application_id, df_applications)

df_applications.to_csv('./results/__ms_applications_extract.csv')


# get list of servers
# for each server save into df
list_of_servers = get_all_servers_list_from_ado()
for server in list_of_servers:
    df_servers = save_server_wi_into_data_frame(server, df_servers)

df_servers.to_csv('./results/__ms_servers_extract.csv')


# map applications with servers
list_of_all_applications = get_all_applications_list_from_ado()
for application_id in list_of_all_applications: 
    df_map_server_vs_app = save_map_server_vs_app(application_id, df_map_server_vs_app)
    
df_map_server_vs_app.to_csv('./results/__ms_mapping.csv')


end_time = time.time()/60 # sec
print(end_time - start_time)
