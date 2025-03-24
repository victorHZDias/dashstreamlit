import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Carrega as variáveis de ambiente
load_dotenv()

def get_db_connection():
    """Cria uma conexão com o banco de dados PostgreSQL"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )

def get_dias_uteis(mes, ano):
    """Retorna o número de dias úteis no mês"""
    # Aqui você pode implementar a lógica para calcular os dias úteis
    # Por enquanto, retornando valores fixos para exemplo
    return [22, 15]  # [dias_uteis, dias_passados]

def get_dados_dashboard(mes, ano, avancado):
    """Retorna os dados do dashboard baseado nas queries fornecidas"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        dias_uteis = get_dias_uteis(mes, ano)
        
        query = """
        WITH
            Liquidado_mensal as (
                SELECT
                EXTRACT('month' from "Data_Liquidacao") as mes_liquidacao,
                lq."Criado_Por" as Colaborador,
                eq."REPORTE" as avancado,
                ROUND(SUM(lq."Valor_Liquidado"::numeric), 2)::numeric as valor_liquidado_mes,
                RANK() OVER (ORDER BY ROUND(SUM(lq."Valor_Liquidado"::numeric), 2) DESC) rank_mensal,
                eq."Foto",
                eq."EMAIL"
                FROM "Liquidado" lq
                RIGHT JOIN "Equipe_Completa" eq ON eq."Nome_Colaborador" = lq."Criado_Por"
                WHERE extract('month' from lq."Data_Liquidacao") = %s
                and extract('year' from lq."Data_Liquidacao") = %s
                and eq."CARGO" = 'ASSISTENTE'
                GROUP BY EXTRACT('month' from "Data_Liquidacao"),
                lq."Criado_Por", eq."REPORTE", eq."Foto", eq."EMAIL"
            ),
            Liquidado_anual as (
                SELECT
                lq."Criado_Por" as Colaborador,
                ROUND(SUM(lq."Valor_Liquidado"::numeric), 2)::numeric as valor_liquidado_ano,
                RANK() OVER (ORDER BY ROUND(SUM(lq."Valor_Liquidado"::numeric), 2) DESC) rank_anual
                FROM "Liquidado" lq
                RIGHT JOIN "Equipe_Completa" eq ON eq."Nome_Colaborador" = lq."Criado_Por"
                WHERE extract('year' from lq."Data_Liquidacao") = %s
                and eq."CARGO" = 'ASSISTENTE'
                GROUP BY lq."Criado_Por"
            ),
            Valor_a_Receber as (
                SELECT
                ar."Criado_Por" as Colaborador,
                ROUND(SUM(ar."Valor_Original"::numeric), 2) as Valor_A_Receber_Mes
                FROM "A_Receber" ar
                RIGHT JOIN "Equipe_Completa" eqp ON eqp."Nome_Colaborador" = ar."Criado_Por"
                WHERE extract('month' from ar."Data_Vencimento") = %s
                and extract('year' from ar."Data_Vencimento") = %s
                and eqp."CARGO" = 'ASSISTENTE'
                and "Parcela" = 1
                GROUP BY ar."Criado_Por"
            ),
            tab_negociado_parcial as (
                SELECT
                np."usuário" as Colaborador,
                ROUND(SUM(case when np."condição_de_pagamento" = 'A vista' 
                    then np."valor_acordo" else np."entrada" end::numeric), 2) as negociado_dia
                FROM negociado_parcial np
                RIGHT JOIN "Equipe_Completa" eqp ON eqp."Nome_Colaborador" = np."usuário"
                WHERE extract('month' from np."criada_em") = %s
                and extract('year' from np."criada_em") = %s
                and eqp."CARGO" = 'ASSISTENTE'
                GROUP BY np."usuário"
            ),
            tab_metas as (
                SELECT mes_num, "Meta_Individual"::numeric
                FROM metas
                WHERE mes_num = %s AND ano = %s
            ),
            Tabela_Geral as (
                SELECT *
                FROM Liquidado_mensal lm
                LEFT JOIN Liquidado_anual la using (colaborador)
                LEFT JOIN Valor_a_Receber va using (colaborador)
                LEFT JOIN tab_negociado_parcial tnp using (colaborador)
                LEFT JOIN tab_metas tm on tm.mes_num = lm.mes_liquidacao
            )
        SELECT
            rank_mensal,
            rank_anual,
            colaborador,
            avancado,
            "Meta_Individual",
            round("Meta_Individual"/%s, 2) as meta_diaria,
            valor_liquidado_mes,
            round((valor_liquidado_mes / "Meta_Individual") * 100, 2) || '%%' as percentual_liquidado,
            case when ("Meta_Individual"-valor_liquidado_mes)<0 then 0
                else "Meta_Individual"-valor_liquidado_mes end as falta_meta,
            round(valor_liquidado_mes-(("Meta_Individual"/%s)*%s), 2) as deficit_superavit,
            CASE WHEN round(valor_liquidado_mes-(("Meta_Individual"/%s)*%s), 2)<0 
                then 'Déficit' ELSE 'Superávit' end as sup_def_cat,
            valor_a_receber_mes,
            negociado_dia,
            valor_liquidado_ano,
            "Foto",
            "EMAIL"
        FROM Tabela_Geral
        WHERE avancado = %s
        ORDER BY rank_mensal
        """
        
        # Parâmetros da query
        params = [
            mes, ano,  # Liquidado_mensal
            ano,       # Liquidado_anual
            mes, ano,  # Valor_a_Receber
            mes, ano,  # tab_negociado_parcial
            mes, ano,  # tab_metas
            dias_uteis[0],  # meta_diaria
            dias_uteis[0], dias_uteis[1],  # deficit_superavit
            dias_uteis[0], dias_uteis[1],  # sup_def_cat
            avancado  # WHERE avancado = %s
        ]
        
        cur.execute(query, params)
        dados = cur.fetchall()
        return dados
        
    finally:
        cur.close()
        conn.close() 