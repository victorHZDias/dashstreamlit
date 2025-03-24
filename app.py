import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from config import USUARIOS_AUTORIZADOS
from database import get_dados_dashboard,get_metas,get_avancado
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

    colab=database.get_avancado()

    avancado=st.sidebar.selectbox("Selecione o Avançado",["ALEX DIAS DA CUNHA","ADOILSON LIMA DO NASCIMENTO","TODOS"])

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
        st.title("📊 Dashboard de Desempenho - Setor de Cobrança")
 
        # Buscar dados do banco
        try:
            dados = get_dados_dashboard(mes, ano, avancado)
            metas=get_metas(mes, ano)
            df = pd.DataFrame(dados)
            
            # Métricas principais
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                valor_total = df['valor_liquidado_mes'].sum()
                meta_total = df['Meta_Individual'].sum()
                percentual_meta = (valor_total / meta_total) * 100
                st.metric("Valor Total Liquidado", f"R$ {valor_total:,.2f}", f"{percentual_meta:.1f}% da meta")

            with col2:
                media_diaria = df['valor_liquidado_mes'].mean()
                st.metric("Média Diária Liquidada", f"R$ {media_diaria:,.2f}")

            with col3:
                taxa_sucesso = (df['valor_liquidado_mes'].sum() / df['valor_a_receber_mes'].sum()) * 100
                st.metric("Taxa de Sucesso", f"{taxa_sucesso:.1f}%")

            with col4:
                valor_pendente = df['valor_a_receber_mes'].sum() - df['valor_liquidado_mes'].sum()
                st.metric("Valor Pendente", f"R$ {valor_pendente:,.2f}")

            # Gráficos
            st.subheader("Desempenho por Colaborador")
            col5, col6 = st.columns(2)

            with col5:
                fig_assistentes = px.bar(df, 
                                       x='colaborador', 
                                       y='valor_liquidado_mes',
                                       title='Valor Liquidado por Colaborador',
                                       labels={'valor_liquidado_mes': 'Valor Liquidado (R$)', 
                                              'colaborador': 'Colaborador'})
                st.plotly_chart(fig_assistentes, use_container_width=True)

            with col6:
                fig_meta = px.bar(df, 
                                x='colaborador', 
                                y=['valor_liquidado_mes', 'Meta_Individual'],
                                title='Valor Liquidado vs Meta Individual',
                                labels={'value': 'Valor (R$)', 'colaborador': 'Colaborador'})
                st.plotly_chart(fig_meta, use_container_width=True)

            # Tabela de dados
            st.subheader("Dados Detalhados")
            tabela_detalhada = df[[
                'colaborador', 'valor_liquidado_mes', 'Meta_Individual',
                'percentual_liquidado', 'falta_meta', 'deficit_superavit',
                'valor_a_receber_mes', 'negociado_dia'
            ]].copy()

            tabela_detalhada.columns = [
                'Colaborador', 'Valor Liquidado', 'Meta Individual',
                '% da Meta', 'Falta Meta', 'Déficit/Superávit',
                'Valor a Receber', 'Negociado'
            ]

            st.dataframe(df.style.format({
                'Valor Liquidado': 'R$ {:,.2f}',
                'Meta Individual': 'R$ {:,.2f}',
                'Valor a Receber': 'R$ {:,.2f}',
                'Negociado': 'R$ {:,.2f}'
            }),hide_index=True)

        except Exception as e:
            st.error(f"Erro ao buscar dados: {str(e)}")
            st.info("Verifique se as configurações do banco de dados estão corretas no arquivo .env")
