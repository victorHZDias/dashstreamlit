import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from config import USUARIOS_AUTORIZADOS
from database import get_dados_dashboard,get_metas,get_avancado,get_dias_uteis
# from database import get_dados_dashboard,get_metas,get_avancado
import json
import os
import locale

# Configurações de localização
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

# Configuração da página
st.set_page_config(page_title="Dashboard de Cobrança", layout="wide")

# Sistema de Login
def verificar_login(username, password):
    if username in USUARIOS_AUTORIZADOS:
        if USUARIOS_AUTORIZADOS[username]['password'] == password and USUARIOS_AUTORIZADOS[username]['ativo']:
            return True, USUARIOS_AUTORIZADOS[username]['role'], USUARIOS_AUTORIZADOS[username]['nome']
    return False, None, None

# Função para salvar alterações nos usuários
def salvar_usuarios():
    # Garantir que os valores booleanos sejam True/False
    usuarios_formatados = {}
    for username, dados in USUARIOS_AUTORIZADOS.items():
        usuarios_formatados[username] = {
            'password': dados['password'],
            'role': dados['role'],
            'nome': dados['nome'],
            'ativo': bool(dados['ativo'])  # Garante que seja True/False
        }
    
    with open('config.py', 'w', encoding='utf-8') as f:
        f.write("# Dicionário de usuários autorizados\n")
        f.write("# Formato: 'username': {'password': 'senha', 'role': 'cargo', 'nome': 'Nome Completo', 'ativo': True}\n")
        f.write("USUARIOS_AUTORIZADOS = ")
        json.dump(usuarios_formatados, f, indent=4, ensure_ascii=False)

# Inicializar a sessão
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.nome = None

# Tela de Login
if not st.session_state.logged_in:
    st.title("🔐 Login - Dashboard de Cobrança")
    
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submit_button = st.form_submit_button("Entrar")
        
        if submit_button:
            sucesso, role, nome = verificar_login(username, password)
            if sucesso:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = role
                st.session_state.nome = nome
                st.success(f"Bem-vindo(a), {nome}!")
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos!")

else:
    # Barra lateral com informações do usuário e logout
    with st.sidebar:
        st.write(f"👤 Usuário: {st.session_state.nome}")
        st.write(f"🎭 Função: {st.session_state.role.title()}")
        
        # Opção de alterar senha para usuários não-admin
        if st.session_state.role != 'admin':
            with st.expander("🔑 Alterar Senha"):
                with st.form("alterar_senha"):
                    senha_atual = st.text_input("Senha Atual", type="password")
                    nova_senha = st.text_input("Nova Senha", type="password")
                    confirmar_senha = st.text_input("Confirmar Nova Senha", type="password")
                    
                    if st.form_submit_button("Alterar Senha"):
                        if senha_atual != USUARIOS_AUTORIZADOS[st.session_state.username]['password']:
                            st.error("Senha atual incorreta!")
                        elif nova_senha != confirmar_senha:
                            st.error("As senhas não coincidem!")
                        else:
                            USUARIOS_AUTORIZADOS[st.session_state.username]['password'] = nova_senha
                            salvar_usuarios()
                            st.success("Senha alterada com sucesso!")
        
        if st.button("Sair"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.role = None
            st.session_state.nome = None
            st.rerun()

    # Menu de navegação
    menu = st.sidebar.selectbox(
        "Menu",
        ["Dashboard", "Gerenciar Usuários"] if st.session_state.role == 'admin' else ["Dashboard"]
    )
    mes=st.sidebar.selectbox("Mês", range(1, 13), format_func=lambda x: datetime(2000, x, 1).strftime('%B'))
    ano=st.sidebar.selectbox("Ano", range(2020, datetime.now().year + 1), index=len(range(2020, datetime.now().year + 1))-1)

    colab=get_avancado()
    colab.append("TODOS")
    avancado=st.sidebar.selectbox("Selecione o Avançado",colab)

    if menu == "Gerenciar Usuários" and st.session_state.role == 'admin':
        st.title("👥 Gerenciamento de Usuários")
        
        # Lista de usuários
        st.subheader("Usuários Cadastrados")
        for username, dados in USUARIOS_AUTORIZADOS.items():
            with st.expander(f"{dados['nome']} ({username})"):
                col1, col2 = st.columns(2)
                with col1:
                    novo_nome = st.text_input("Nome", value=dados['nome'], key=f"nome_{username}")
                    novo_role = st.selectbox("Função", ["admin", "avancado", "assistente"], 
                                           index=["admin", "avancado", "assistente"].index(dados['role']),
                                           key=f"role_{username}")
                with col2:
                    novo_password = st.text_input("Nova Senha", type="password", value="", key=f"pass_{username}")
                    ativo = st.checkbox("Usuário Ativo", value=dados['ativo'], key=f"ativo_{username}")
                
                col3, col4 = st.columns(2)
                with col3:
                    if st.button("Atualizar", key=f"update_{username}"):
                        USUARIOS_AUTORIZADOS[username]['nome'] = novo_nome
                        USUARIOS_AUTORIZADOS[username]['role'] = novo_role
                        if novo_password:
                            USUARIOS_AUTORIZADOS[username]['password'] = novo_password
                        USUARIOS_AUTORIZADOS[username]['ativo'] = ativo
                        salvar_usuarios()
                        st.success("Usuário atualizado com sucesso!")
                
                with col4:
                    if st.button("Excluir", key=f"delete_{username}"):
                        if username != st.session_state.username:
                            del USUARIOS_AUTORIZADOS[username]
                            salvar_usuarios()
                            st.success("Usuário excluído com sucesso!")
                            st.rerun()
                        else:
                            st.error("Você não pode excluir seu próprio usuário!")

        # Adicionar novo usuário
        st.subheader("Adicionar Novo Usuário")
        with st.form("novo_usuario"):
            novo_username = st.text_input("Username", key="novo_username")
            novo_nome = st.text_input("Nome Completo", key="novo_nome")
            novo_password = st.text_input("Senha", type="password", key="novo_password")
            novo_role = st.selectbox("Função", ["admin", "avancado", "assistente"], key="novo_role")
            
            if st.form_submit_button("Adicionar"):
                if novo_username not in USUARIOS_AUTORIZADOS:
                    USUARIOS_AUTORIZADOS[novo_username] = {
                        'password': novo_password,
                        'role': novo_role,
                        'nome': novo_nome,
                        'ativo': True
                    }
                    salvar_usuarios()
                    st.success("Usuário adicionado com sucesso!")
                    st.rerun()
                else:
                    st.error("Username já existe!")

    else:
        # Título do dashboard
        st.title("📊Desempenho - Setor de Cobrança")
 
        # Buscar dados do banco
        try:
            dados = get_dados_dashboard(mes, ano, avancado)
            metas=get_metas(mes, ano)
            dias_uteis = get_dias_uteis(mes, ano)
            df = pd.DataFrame(dados[0])
            # Métricas principais
            col1, col2, col3, col4 = st.columns(4)

            with col1:

                valor_total = dados[1]
                meta_total = metas["Meta_Geral"]
                percentual_meta = (valor_total / meta_total) * 100
                st.metric("Valor Total Liquidado", f"R$ {valor_total:,.2f}", f"{percentual_meta:.1f}% da meta")

            with col2:
                media_diaria = meta_total/dias_uteis[0]
                st.metric("Média Diária Liquidada", f"R$ {media_diaria:,.2f}")

            with col3:
                taxa_sucesso = (df['valor_liquidado_mes'].sum() / df['valor_a_receber_mes'].sum()) * 100
                st.metric("Taxa de Sucesso", f"{taxa_sucesso:.1f}%")

            with col4:
                valor_pendente = df['valor_a_receber_mes'].sum() - df['valor_liquidado_mes'].sum()
                st.metric("Valor Pendente", f"R$ {valor_pendente:,.2f}")

            # Gráficos
            col5, col6 = st.columns(2)
            dfAvan = df.groupby('avancado', as_index=False)['valor_liquidado_mes'].sum().sort_values('valor_liquidado_mes', ascending=False)

            with col5:
                with st.container(border=True):
                    dfAssist = df.sort_values('valor_liquidado_mes')
                    fig_meta = go.Figure()

                    # Adicionar barras de valor liquidado
                    fig_meta.add_trace(go.Bar(
                        y=dfAssist['colaborador'],
                        x=dfAssist['valor_liquidado_mes'],
                        orientation='h',
                        name='Valor Liquidado',
                        marker=dict(
                            color='blue',  # Azul como cor principal
                            opacity=0.8,
                            line=dict(width=1.5, color='blue'),
                            cornerradius=3
                        )
                    ))

                    # Adicionar barras de valor a receber
                    fig_meta.add_trace(go.Bar(
                        y=dfAssist['colaborador'],
                        x=dfAssist['valor_a_receber_mes'],
                        orientation='h',
                        name='Valor a Receber',
                        marker=dict(
                            color='lightblue',  # Tons de azul para destaque
                            opacity=0.6,
                            line=dict(width=1.5, color='lightblue'),
                            cornerradius=3
                        )
                    ))

                    # Adicionar linha de meta
                    fig_meta.add_trace(go.Scatter(
                        y=df['colaborador'],
                        x=df['Meta_Individual'],
                        mode='lines',
                        name='Meta Individual',
                        line=dict(color='red', width=4, dash='dot')  # Vermelho para chamar atenção
                    ))

                    fig_meta.update_layout(
                        title='Valor Liquidado e Valor a Receber vs Meta Individual',
                        xaxis_title='Valor (R$)',
                        yaxis_title='Colaborador',
                        barmode='stack',  # Empilhamento das barras
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        height=750,  # Aumentar a altura do gráfico
                        margin=dict(l=200)  # Aumentar a margem esquerda para acomodar os nomes
                    )

                    # Reduzir o tamanho do texto no eixo Y para caber todos os nomes
                    fig_meta.update_yaxes(tickfont=dict(size=10), automargin=True)

                    st.plotly_chart(fig_meta, use_container_width=True)

            with col6:
                with st.container(border=True, height=300):
                    # Gráfico Gauge baseado no percentual liquidado em relação à meta
                    percentual_liquidado = round((valor_total / meta_total) * 100, 2)
                    fig_gauge = go.Figure(go.Indicator(
                                mode="gauge+number+delta",
                                value=percentual_liquidado,
                                domain={'x': [0, 1], 'y': [0, 1]},
                                gauge={
                                    'axis': {'range': [None, 100], 'tickwidth': 1},
                                    'bar': {'color': "blue"},  # Azul para barra do gauge
                                    'borderwidth': 3, 'bordercolor': "lightblue"  # Tons de azul para borda
                                },
                                delta={'reference': 100, 'increasing': {'color': "skyblue"}},  # Tons de azul para delta
                                ))
                    fig_gauge.update_layout(
                        width=300,  # Reduz a largura do gráfico
                        height=250,  # Reduz a altura do gráfico
                        margin=dict(l=10, r=10, t=20, b=10),  # Ajusta margens para centralizar
                        paper_bgcolor="rgba(0,0,0,0)",  # Fundo transparente
                        title='Liquidado vs Meta (%)',
                    )
                    st.plotly_chart(fig_gauge, use_container_width=True)  # Ajusta largura ao container
                with st.container(border=True,height=465):
                    fig_assistentes = px.bar(dfAvan,
                                            x='avancado', 
                                            y='valor_liquidado_mes',
                                            labels={'valor_liquidado_mes': 'Valor Liquidado (R$)', 
                                                    'avancado': 'Avançado'}
                                            )
                    fig_assistentes.update_yaxes(range=[0, 1_000_000])  # Define o limite do eixo Y para 1 milhão
                    fig_assistentes.update_layout(
                        margin=dict(l=8, r=8, t=20, b=1),  # Ajusta margens para centralizar
                        width=350,  # Reduz a largura do gráfico
                        height=400,  # Reduz a altura do gráfico
                        paper_bgcolor="rgba(0,0,0,0)",  # Fundo transparente
                        title='Valor Liquidado por equipe',
                    )
                    st.plotly_chart(fig_assistentes, use_container_width=True)
                    # Gráfico de pódio com os 10 primeiros do rank anual

            # Tabela de dados
            st.subheader("Dados Detalhados")
            tabela_detalhada = df[[
                            'rank_mensal', 'rank_anual', 'colaborador', 'avancado',
                            'Meta_Individual', 'meta_diaria', 'valor_liquidado_mes',
                            'percentual_liquidado', 'falta_meta', 'deficit_superavit',
                            'sup_def_cat', 'valor_a_receber_mes', 'negociado_dia',
                            'valor_liquidado_ano']].copy()

            # tabela_detalhada.columns = [
            #     'Rank Mensal','Rank Anual','Colaborador', 'Avancado', 'Meta Individual', 'Meta Diaria','Valor Liquidado',
            #     '% da Meta', 'Falta Meta', 'Déficit/Superávit','sup_def_cat',
            #     'Valor a Receber', 'Negociado','valor_liquidado_ano'
            # ]

            with st.expander("Exibir Tabela"):
                st.dataframe(tabela_detalhada.fillna(0).style.format({
                    'valor_liquidado_mes': 'R$ {:,.2f}',
                    'Meta_Individual': 'R$ {:,.2f}',
                    'valor_a_receber_mes': 'R$ {:,.2f}',
                    'negociado_dia': 'R$ {:,.2f}'
                }),hide_index=True)
                
            st.subheader("🏅 Top 10 - Rank Mensal e Anual")
            try:
                # Filtrar os 10 primeiros do rank mensal e anual
                top_10_mensal = df.nsmallest(10, 'rank_mensal')
                top_10_anual = df.nsmallest(10, 'rank_anual')

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("### 🏅 Rank Mensal")
                    for i, row in top_10_mensal.iterrows():
                        col_img, col_text = st.columns([1, 4])
                        with col_img:
                            if 'Foto' in row and row['Foto']:
                                st.image(row['Foto'], width=50, caption=f"#{row['rank_mensal']}")
                            else:
                                st.text(f"#{row['rank_mensal']}")
                        with col_text:
                            st.markdown(f"**{row['colaborador']}**")
                            st.markdown(f"Valor Liquidado Mensal: R$ {row['valor_liquidado_mes']:,.2f}")
                        st.markdown("---")

                with col2:
                    st.markdown("### 🏆 Rank Anual")
                    for i, row in top_10_anual.iterrows():
                        col_img, col_text = st.columns([1, 4])
                        with col_img:
                            if 'Foto' in row and row['Foto']:
                                st.image(row['Foto'], width=50, caption=f"#{row['rank_anual']}")
                            else:
                                st.text(f"#{row['rank_anual']}")
                        with col_text:
                            st.markdown(f"**{row['colaborador']}**")
                            st.markdown(f"Valor Liquidado Anual: R$ {row['valor_liquidado_ano']:,.2f}")
                        st.markdown("---")

            except Exception as e:
                st.error(f"Erro ao gerar os rankings: {str(e)}")

        except Exception as e:
            st.error(f"Erro ao buscar dados: {str(e)}")
            st.info("Verifique se as configurações do banco de dados estão corretas no arquivo .env")
