import os
import subprocess


def binlog2sql_command(path, host, user, password, binlog_file, div):
    
    # 포지션 번호
    if div == "P" or div =="p":

        print("\n")
        START_POSITION = input("START POSITION : ")
        STOP_POSITION = input("STOP  POSITION : ")

        if STOP_POSITION == "":
            
            COMMAND_OPTION = " --start-position " + str(START_POSITION) + " "
        
        else:
            COMMAND_OPTION = " --start-position " + str(START_POSITION) + " --stop-position " + str(STOP_POSITION)
    
    # 날짜
    elif div == "D" or div == "d":

        print("\n")
        START_DATETIME = input("START DATETIME(%Y-%m-%d %H:%M:%S) : ")
        STOP_DATETIME = input("STOP  DATETIME(%Y-%m-%d %H:%M:%S) : ")

        if STOP_DATETIME == "":

            COMMAND_OPTION = " --start-datetime '" + str(START_DATETIME) + "' "
        
        else:

            COMMAND_OPTION = " --start-datetime '" + str(START_DATETIME) + "' --stop-datetime '" + str(STOP_DATETIME) + "'"
        

    execute_sql_command = path + " --host "+ host + \
                                 " --user "+ user + \
                                 " --password '" + password + "'" \
                                 " --only-dml" \
                                 " --start-file " + binlog_file + \
                                 COMMAND_OPTION + " | cut -f1 -d'#'"
                     
    
    rollback_sql_command = path + " --host "+ host + \
                                  " --user "+ user + \
                                  " --password '" + password + "'" \
                                  " --only-dml" \
                                  " --start-file " + binlog_file + \
                                  COMMAND_OPTION + \
                                  " --flashback | awk -F\" \" '{print $(NF-1), $NF, $0}' | sort | cut -f1 -d'#' | cut -d \" \" -f3-"


    return execute_sql_command, rollback_sql_command



def os_execute_command(command):
    popen = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (stdoutdata, stderrdata) = popen.communicate()

    return stdoutdata, stderrdata



def main():

    PYTHON_PATH = os_execute_command("which python3")
    PYTHON_PATH = PYTHON_PATH[0].decode('utf-8').strip()

    BINLOG2SQL_PATH = os_execute_command("find /Users -type f -name binlog2sql.py -print 2>/dev/null")
    BINLOG2SQL_PATH = BINLOG2SQL_PATH[0].decode('utf-8').strip()
    if BINLOG2SQL_PATH == "":
        
        INSTALL_GUIDE = """
            # "binlog2sql" INSTALL COMMAND 
            1) git clone https://github.com/danfengcao/binlog2sql.git && cd binlog2sql
            2) pip install -r requirements.txt
            3) pip install pymysql==0.9.3
        """
        print(INSTALL_GUIDE)
        exit()

    PATH = PYTHON_PATH + " " + BINLOG2SQL_PATH 
    os.system("clear")
    print("\n")

    HOST = input("HOST : ")
    USER = input("USER : ")
    PASSWD = input("PASSWD : ")
    BINLOG_FILE_NM = input("BinLog File Name(SHOW MASTER STAUTS) : ")
    DIV_P_D =input("P(Position) or D(Datetime) : ")

    EXECUTE_SQL_LIST = []
    ROLLBACK_SQL_LIST = []

    EXECUTE_SQL_COMMAND, ROLLBACK_SQL_COMMAND = binlog2sql_command(PATH, HOST, USER, PASSWD, BINLOG_FILE_NM, DIV_P_D)
    EXECUTE_SQL = os_execute_command(EXECUTE_SQL_COMMAND)
    EXECUTE_SQL = EXECUTE_SQL[0].decode('utf-8').replace(" \n","").strip()
    EXECUTE_SQL_LIST = EXECUTE_SQL.split(";")

    ROLLBACK_SQL = os_execute_command(ROLLBACK_SQL_COMMAND)
    ROLLBACK_SQL = ROLLBACK_SQL[0].decode('utf-8').replace(" \n","").strip()
    ROLLBACK_SQL_LIST = ROLLBACK_SQL.split(";")
    #print(ROLLBACK_SQL_LIST, len(ROLLBACK_SQL_LIST))
    

    for i in range(len(EXECUTE_SQL_LIST)):

        if EXECUTE_SQL_LIST[i] == "":
            continue
    
        print("\n")
        print("-- No." + str(i + 1))
        print("EXECUTE  : " + EXECUTE_SQL_LIST[i] + ";")
        print("ROLLBACK : " + ROLLBACK_SQL_LIST[i] + ";")
        print("-- -------------------------------------------------------------------------------------------")


if __name__ == "__main__":
    
    main()