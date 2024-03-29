#!/usr/bin/python3

import psycopg2


def dados_tempo():
    print("DADOS TEMPO")
    cur.execute("""select date_part('hour', timestamp) as h,
                          date_part('day', timestamp) as d, 
                          date_part('month', timestamp) as m
                   from (select to_timestamp(initial_ts) as timestamp from taxi_services) as S
                   group by h,d,m;""")
    rows = cur.fetchall()
    for row in rows:
        cur.execute("""INSERT INTO tempo (hora, dia, mes) 
                       VALUES(%s, %s, %s);""", (row[0], row[1], row[2]))


def dados_taxi():
    print("DADOS TAXI")
    cur.execute("""select DISTINCT(taxi_id) as id from taxi_services order by id""")
    rows = cur.fetchall()
    for row in rows:
        cur.execute("""INSERT INTO taxi (n_licenca) VALUES(%s);""", [(row[0])])


def dados_stand():
    print("DADOS STAND")
    cur.execute("""select name from taxi_stands;""")
    rows = cur.fetchall()
    for row in rows:
        cur.execute("""INSERT INTO stand (nome, lotacao) VALUES(%s, %s);""", (row[0], 1))


def dados_local():
    print("DADOS LOCAL")
    cur.execute("""select stand_id, nome from stand;""")
    rows = cur.fetchall()
    for row in rows:
        stand_id = row[0]
        cur.execute("""select freguesia, concelho 
                       from caop, taxi_stands 
                       where taxi_stands.id = %s 
                       and st_contains(caop.geom, taxi_stands.location);""",
                       [stand_id])
        rows2 = cur.fetchall()
        freg = rows2[0][0]
        conc = rows2[0][1]
        cur.execute("""INSERT INTO local(stand_id, freguesia, concelho) 
                       VALUES(%s,%s,%s);""", (stand_id, freg, conc))


def dados_services():
    print("DADOS SERVICES")
    cur.execute("""select * from taxi;""")
    taxis = cur.fetchall()
    for taxi in taxis:
        taxi_id, n_licenca = taxi[0], taxi[1]
        print(taxi_id)
        cur.execute("""select date_part('hour', to_timestamp(initial_ts)) as hour,
                              date_part('day', to_timestamp(initial_ts)) as day,
                              date_part('month', to_timestamp(initial_ts)) as month,
                              (SELECT ts1.id from taxi_stands as ts1 
                              ORDER BY st_distance(ts1.location, serv.initial_point) LIMIT 1),
                              (SELECT ts1.id from taxi_stands as ts1 
                              ORDER BY st_distance(ts1.location, serv.final_point) LIMIT 1),
                              count(*), 
                              sum(EXTRACT(EPOCH FROM(to_timestamp(serv.final_ts) 
                                  - to_timestamp(serv.initial_ts)))/60)
                       from taxi_services as serv 
                       where taxi_id = %s 
                       group by  1,2,3,4,5 order by 6 DESC;""", [n_licenca])

        all_rows = cur.fetchall()
        for row in all_rows:
            hora, dia, mes, stand_inicio, stand_fim = row[0], row[1], row[2], row[3], row[4]
            n_viagens, tempo_total = row[5], row[6]
            cur.execute("""select tempo_id from tempo where hora=%s and dia=%s and mes=%s;""", (hora, dia, mes))
            fetch_tempo = cur.fetchall()
            tempo_id = fetch_tempo[0][0]
            cur.execute("""select local_id from local where stand_id=%s;""", [stand_inicio])
            fetch_inicio = cur.fetchall()
            local_id_inicio = fetch_inicio[0][0]
            cur.execute("""select local_id from local where stand_id=%s;""", [stand_fim])
            fetch_fim = cur.fetchall()
            local_id_fim = fetch_fim[0][0]
            cur.execute("""insert into services(taxi_id, tempo_inicio_id, local_inicio_id, local_fim_id, tempo_total, n_viagens) 
                           VALUES(%s, %s, %s, %s, %s, %s);""",
                           (taxi_id, tempo_id, local_id_inicio, local_id_fim, tempo_total, n_viagens))


if __name__ == "__main__":
    try:
        conn = psycopg2.connect("dbname='trabalho' user='tiaghoul' host='localhost' password=''")
        conn.autocommit = True
        cur = conn.cursor()

        dados_tempo()
        dados_taxi()
        dados_stand()
        dados_local()
        dados_services()

        cur.close()
        conn.close()

    except ConnectionError:
        print("I am unable to connect to the database")

