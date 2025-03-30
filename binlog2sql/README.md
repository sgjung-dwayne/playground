
---
- DB 빈로그(Binlog) 파일 내용을 가공하여 → 롤백 SQL 추출
- 빈로그 파일로 활용 하기에는 제한 사항이 있음
	- 컬럼 네이밍을 별도로 확인해서 매핑해야 함(ex @1, @2 …)
    - ex) 빈로그 파일

binlog2sql

---
- Cao Danfeng(중국 사람?)이 개발한 오픈 소스
- 빈로그를 활용하여 롤백 SQL 추출 가능 → PITR(Point In Time Recovery) 가능
- 참고 링크
	- https://github.com/danfengcao/binlog2sql
	- https://www.percona.com/blog/2020/07/09/binlog2sql-binlog-to-raw-sql-conversion-and-point-in-time-recovery/
	- https://kimdubi.github.io/mysql/flashback/#binlog2sql

binlog2sql 테스트

- binlog2sql 수행하기 위한 필수 DB 설정(케어닥 개발,운영 DB에는 설정되어 있음)
	- [MySQL] binlog_format = ROW
	- [MySQL] binlog_row_image = FULL
		- 참고 : https://dev.mysql.com/doc/internals/en/binlog-row-image.html 
1. binlog2sql 설치
```
cmd> git clone <https://github.com/danfengcao/binlog2sql.git> && cd binlog2sql
cmd> pip install -r requirements.txt
cmd> pip install pymysql==0.9.3

```
2. binlog2sql 실행
	- 빈로그 → SQL
```python
--# 포지션 번호로 추출
python binlog2sql.py -h{DB Host} \
                     -u{DB User} -p   \
                     --only-dml \
                     --start-file mysql-bin-changelog.000007 \
                     --start-position 118449595 --stop-position 118452047 | cut -f1 -d'#'

--# 날짜로 추출
python binlog2sql.py -h{DB Host} \
                     -u{DB User} -p   \
                     --only-dml \
                     --start-file mysql-bin-changelog.000007 \
                     --start-datetime '2024-08-22 11:00:00' | cut -f1 -d'#'

```
- 빈로그 → 롤백 SQL(flashback)
```python
--# 포지션 번호로 추출
python binlog2sql.py -h{DB Host} \
                     -u{DB User} -p   \
                     --only-dml \
                     --start-file mysql-bin-changelog.000007 \
                     --start-position 118449595 --stop-position 118452047 \
                     --flashback** | awk -F" " '{print $NF, $0}' | sort | cut -f1 -d'#' | cut -d " " -f2-

--# 날짜로 추출
python binlog2sql.py -h{DB Host} \
                     -u{DB User} -p   \
                     --only-dml \
                     --start-file mysql-bin-changelog.000007 \
                     --start-datetime '2024-08-22 11:00:00' \
                     --flashback** | awk -F" " '{print $NF, $0}' | sort | cut -f1 -d'#' | cut -d " " -f2-
```