"""
    IDC --> AWS 이관용 스크립트(1회성)
    - OS : Linux(ex ec2 → /home/centos/python-script/dms/dms_task_create.py)

    * DMS 복제 인스턴스는 UI에서 생성해야 함
    * AWS Access Key, Secret Key 입력 후 스크립트 수행(aws_access_key_id, aws_secret_access_key)
    * DB 계정,패스워드 입력 후 스크립트 수행(db_user/pw, source_db_user/pw)
    * 태스크 생성 후 UI에서 복제 인스턴스와 연결 테스트 필수
"""
import boto3
import pymysql
import os

db_user = ''
db_pw = ''

client = boto3.client(
    'dms',
    aws_access_key_id='',
    aws_secret_access_key='',
    region_name='ap-northeast-2'
)


def dms_table_mapping(v_source_ip,v_source_tab):

    source_db_user = ''
    source_db_pw = ''
    source_db_ip = v_source_ip
    source_conn = pymysql.connect(host=source_db_ip, port=3306, user=source_db_user, password=source_db_pw)

    source_curs = source_conn.cursor()
    source_schema_sql = "SELECT DISTINCT table_schema\n" \
                        "FROM   information_schema.TABLES\n" \
                        "WHERE  table_schema NOT IN ('information_schema','performance_schema','sys','mysql')\n" \
                        "AND    table_schema IN (" + v_source_tab + ")\n"
    source_curs.execute(source_schema_sql)
    schema_result = source_curs.fetchall()
    source_conn.close()
    source_curs.close()

    json_no = 0
    mapping_json = ""
    
    for x in range(len(schema_result)):

        schema = schema_result[x][0]
        json_no += 1

        include_json = """{"rule-type":"selection","rule-id":"%s","rule-name":"%s","object-locator":{"schema-name":"%s","table-name":"%%"},"rule-action":"include","filters":[]},"""
        mapping_json += (include_json %(json_no,json_no,schema))

       
        #for j in range(len(except_table_list)):
        #    except_table = except_table_list[j]
        #    json_no += 1
        #    except_json = """{"rule-type":"selection","rule-id":"%s","rule-name":"%s","object-locator":{"schema-name":"%s","table-name":"%s"},"rule-action":"exclude","filters":[]},"""
        #    mapping_json += (except_json % (json_no, json_no, schema, except_table))

    

    return str(mapping_json)


def dms_describe(v_name, v_value):
    describe_value = ""
    if v_name == "instance":
        describe_value = client.describe_replication_instances(
            Filters=({'Name': 'replication-instance-class', 'Values': [v_value]},),
            MaxRecords=100,
            Marker='string'
        )
    elif v_name == "endpoint":
        describe_value = client.describe_endpoints(
            Filters=({'Name': 'endpoint-type', 'Values': [v_value]},),
            MaxRecords=100,
            Marker='string'
        )

    return describe_value


def dms_create_endpoint(v_name, v_type, v_user, v_pass, v_ip, v_port):
    create_endpoint = client.create_endpoint(
        EndpointIdentifier=v_name,
        EndpointType=v_type,
        EngineName="mysql",
        Username=v_user,
        Password=v_pass,
        ServerName=v_ip,
        Port=v_port
    )
    return create_endpoint


def dms_create_task(v_task_nm, v_source_ip, v_source_arn, v_target_arn, v_instance_arn):
    os.system('clear')
    print('----------------------------------------------------------------------------')
    print('STEP 4-1. Setting DMS Task')
    print('----------------------------------------------------------------------------')
    print('Source 엔드포인트(',v_source_ip,') 이관 DB 설정')
    v_source_tab = input('Source DB명 입력 : ')
    print('----------------------------------------------------------------------------')

    create_task = client.create_replication_task(
        ReplicationTaskIdentifier=v_task_nm,
        SourceEndpointArn=v_source_arn,
        TargetEndpointArn=v_target_arn,
        ReplicationInstanceArn=v_instance_arn,
        MigrationType='full-load',

        TableMappings='{"rules":['+ dms_table_mapping(v_source_ip,v_source_tab) +']}',
        ReplicationTaskSettings="""{
                "Logging":{
                    "EnableLogging":true
                },
                "FullLoadSettings":{
                    "TargetTablePrepMode":"TRUNCATE_BEFORE_LOAD"
                },
                "ValidationSettings":{
                    "EnableValidation":true,
                    "PartitionSize":1000000,
                    "ThreadCount":20
                },"TargetMetadata":{
                    "SupportLobs":true,
                    "LobChunkSize": 0,
                    "ParallelLoadThreads":0,
                    "LobMaxSize":1024,
                    "LimitedSizeLobMode":true
                }
        }"""
    )
    return create_task


os.system('clear')
print('----------------------------------------------------------------------------')
print('STEP 1-1. Search Replication Instance')
print('----------------------------------------------------------------------------')
replication_instance_type = input('DMS Replication Instance 타입 입력(ex. dms.c5.4xlarge) : ')
print('----------------------------------------------------------------------------')
try:
    replication_instance = dms_describe('instance', replication_instance_type.strip())
    replication_instance = replication_instance['ReplicationInstances']
    for i in range(len(replication_instance)):
        replication_instance_nm = replication_instance[i]['ReplicationInstanceIdentifier']
        replication_instance_arn = replication_instance[i]['ReplicationInstanceArn']
        print("{},\t{}".format(replication_instance_nm, replication_instance_arn))
except Exception as error:
    print("DMS Instance가 존재하지 않습니다.")
    print("에러 내용 : %s" % error)
    print('----------------------------------------------------------------------------')

# 복제 인스턴스 1개만 있을경우 입력 없이 진행
if len(replication_instance) == 1:
    replication_instance_arn = replication_instance_arn
else:
    print('----------------------------------------------------------------------------')
    replication_instance_arn = input('사용할 DMS instance ARN 입력(위 리스트에서 복사) : ')


while True:
    os.system('clear')
    print('----------------------------------------------------------------------------')
    print('STEP 2. Search Source Endpoint')
    print('----------------------------------------------------------------------------')
    endpoint = dms_describe('endpoint', 'source')
    endpoint = endpoint['Endpoints']
    for i in range(len(endpoint)):
        source_endpoint_nm = endpoint[i]['EndpointIdentifier']
        source_endpoint_ip = endpoint[i]['ServerName']
        source_endpoint_arn = endpoint[i]['EndpointArn']

        if "rds" in source_endpoint_ip:
            continue

        print("{},\t{},\t{}".format(source_endpoint_nm, source_endpoint_ip, source_endpoint_arn))

    print('----------------------------------------------------------------------------')

    source_endpoint_ip = input('사용할 Source Endpoint IP 입력(위 리스트에서 복사 / 생성할 경우 C 입력) : ')
    if source_endpoint_ip == 'c' or source_endpoint_ip == 'C':
        os.system('clear')
        print('----------------------------------------------------------------------------')
        print('STEP 2-1. CREATE Source Endpoint')
        print('----------------------------------------------------------------------------')
        endpoint_nm = input('Source Endpoint명 입력 : ')
        endpoint_type = 'source'
        endpoint_ip = input('Source DB IP 입력 : ')

        new_endpoint = dms_create_endpoint(endpoint_nm.strip(), endpoint_type.strip(), db_user, db_pw, endpoint_ip.strip(), 3306)
        new_endpoint_nm = new_endpoint['Endpoint']['EndpointIdentifier']
        new_endpoint_ip = new_endpoint['Endpoint']['ServerName']
        new_endpoint_arn = new_endpoint['Endpoint']['EndpointArn']
        print('----------------------------------------------------------------------------')
        print('생성한 Source Endpoint 정보')
        print("{},\t{},\t{}".format(new_endpoint_nm, new_endpoint_ip, new_endpoint_arn))
        source_endpoint_ip = new_endpoint_ip
        source_endpoint_arn = new_endpoint_arn

    else:
        source_endpoint_arn = input('사용할 Source Endpoint ARN 입력 : ')
    os.system('clear')
    print('----------------------------------------------------------------------------')
    print('STEP 3. Search Target Endpoint')
    print('----------------------------------------------------------------------------')
    target_endpoint = dms_describe('endpoint', 'target')
    target_endpoint = target_endpoint['Endpoints']
    for i in range(len(target_endpoint)):
        target_endpoint_nm = target_endpoint[i]['EndpointIdentifier']
        target_endpoint_ip = target_endpoint[i]['ServerName']
        target_endpoint_arn = target_endpoint[i]['EndpointArn']
        

        print("%-19s : %s" % (target_endpoint_nm, target_endpoint_arn))
    print('----------------------------------------------------------------------------')
    target_endpoint_arn = input('사용할 Target Endpoint ARN 입력(위 리스트에서 복사 / 생성할 경우 C 입력) : ')
    if target_endpoint_arn == 'c' or target_endpoint_arn == 'C':
        os.system('clear')
        print('----------------------------------------------------------------------------')
        print('STEP 3-1. CREATE Target Endpoint')
        print('----------------------------------------------------------------------------')
        endpoint_nm = input('Target Endpoint명 입력 : ')
        endpoint_type = 'target'
        endpoint_ip = input('Target DB IP 입력 : ')


        new_endpoint = dms_create_endpoint(endpoint_nm.strip(), endpoint_type.strip(), db_user, db_pw, endpoint_ip.strip(), 3306)
        new_endpoint_nm = new_endpoint['Endpoint']['EndpointIdentifier']
        new_endpoint_ip = new_endpoint['Endpoint']['ServerName']
        new_endpoint_arn = new_endpoint['Endpoint']['EndpointArn']
        print('----------------------------------------------------------------------------')
        print('생성한 Target Endpoint 정보')
        print("%-19s : %s" % (new_endpoint_nm, new_endpoint_arn))
        target_endpoint_arn = new_endpoint_arn

    os.system('clear')
    print('----------------------------------------------------------------------------')
    print('STEP 4. CREATE DMS Task')
    print('----------------------------------------------------------------------------')
    print('위 단계에서 입력한 정보')
    print('Replication Instance ARN : %-25s' %(replication_instance_arn))
    print('DMS Source Endpoint IP   : %-25s' %(source_endpoint_ip))
    print('DMS Source Endpoint ARN  : %-25s' %(source_endpoint_arn))
    print('DMS Target Endpoint ARN  : %-25s' %(target_endpoint_arn))
    print('----------------------------------------------------------------------------')
    task_nm = input('DMS Task명 입력 : ')

    try:
        dms_create_task(task_nm, source_endpoint_ip, source_endpoint_arn, target_endpoint_arn, replication_instance_arn)
        print("DMS Task Create Success !!")
    except Exception as error:
        os.system('clear')
        print("DMS Task Create Error")
        print("에러 내용 : %s" % error)

    print('----------------------------------------------------------------------------')
    add_task_yn = input('DMS Task 추가 생성 여부 (Y:추가/N:종료) : ')
    if add_task_yn == 'N' or add_task_yn == 'n':
        break