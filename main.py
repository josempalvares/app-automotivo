import flet as ft
import urllib.parse
import webbrowser
import database as db
import psycopg2.extras
import os # Pacote adicionado para capturar a porta do servidor web

def main(page: ft.Page):
    page.title = "App Automotivo"
    try:
        page.window.width = 420
        page.window.height = 820
    except Exception:
        pass
    page.theme_mode = "light"
    page.padding = 0

    def criar_botao(texto, acao_clique, cor_fundo="#1976D2", cor_texto="white", largura=350, altura=45, expandir=False):
        return ft.Container(
            content=ft.Row([ft.Text(texto, color=cor_texto, weight="bold", size=14)], alignment="center"),
            bgcolor=cor_fundo, width=largura, height=altura, border_radius=8, ink=True, on_click=acao_clique, expand=expandir, padding=10
        )

    def criar_pedido(cliente_id, prestador_id):
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pedidos (cliente_id, prestador_id, modalidade, status, lat_cliente, lon_cliente) 
            VALUES (%s, %s, 'delivery', 'pendente', -19.9386, -43.9341)
        ''', (cliente_id, prestador_id))
        conn.commit()
        conn.close()

    def buscar_pedidos_prestador(prestador_id):
        conn = db.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute('''
            SELECT p.id, p.status, p.lat_cliente, p.lon_cliente, u.nome as cliente_nome, u.telefone as cliente_telefone 
            FROM pedidos p
            JOIN usuarios u ON p.cliente_id = u.id
            WHERE p.prestador_id = %s
            ORDER BY p.id DESC
        ''', (prestador_id,))
        pedidos = cursor.fetchall()
        conn.close()
        return [dict(p) for p in pedidos]

    def marcar_pedido_aceito(pedido_id, prestador_id):
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE pedidos SET status = 'aceito', taxa_match_cobrada = 1.00 WHERE id = %s", (pedido_id,))
        cursor.execute("UPDATE prestadores_detalhes SET total_matches_mes = total_matches_mes + 1, saldo_devedor_matches = saldo_devedor_matches + 1.00 WHERE usuario_id = %s", (prestador_id,))
        conn.commit()
        conn.close()

    def mostrar_tela(nome_tela, usuario_logado=None):
        page.clean()

        if nome_tela == "login":
            txt_telefone = ft.TextField(label="Telefone Cadastrado", width=350)
            txt_senha = ft.TextField(label="Senha", password=True, width=350)
            lbl_erro = ft.Text("", color="red", weight="bold")

            def btn_login_click(e):
                conn = db.get_connection()
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute("SELECT id, nome, tipo_perfil FROM usuarios WHERE telefone = %s AND senha_hash = %s", (txt_telefone.value, txt_senha.value))
                user = cursor.fetchone()
                conn.close()
                
                if user:
                    user_dict = dict(user)
                    if user_dict['tipo_perfil'] == 'admin': mostrar_tela("admin")
                    elif user_dict['tipo_perfil'] == 'cliente': mostrar_tela("cliente_home", user_dict)
                    elif user_dict['tipo_perfil'] == 'prestador': mostrar_tela("prestador_home", user_dict)
                else:
                    lbl_erro.value = "❌ Telefone ou senha inválidos!"
                    page.update()

            cabecalho = ft.Container(content=ft.Text("Acesso ao Sistema", color="white", size=20, weight="bold"), bgcolor="#0D47A1", padding=15, width=420)
            corpo = ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Container(height=10), ft.Text("🚗", size=65), ft.Text("App Automotivo", size=24, weight="bold"),
                    ft.Container(height=15), txt_telefone, txt_senha, lbl_erro,
                    criar_botao("Entrar", btn_login_click, "#1976D2", "white", 350, 48),
                    ft.Row([
                        ft.TextButton("Esqueci minha senha", on_click=lambda e: mostrar_tela("recuperar_senha")),
                        ft.TextButton("Criar conta", on_click=lambda e: mostrar_tela("cadastro_escolha"))
                    ], alignment="spaceBetween", width=350)
                ], horizontal_alignment="center")
            )
            page.add(cabecalho, corpo)

        elif nome_tela == "cadastro_escolha":
            cabecalho = ft.Container(content=ft.Text("Criar Nova Conta", color="white", size=20, weight="bold"), bgcolor="#0D47A1", padding=15, width=420)
            corpo = ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Text("Como você deseja usar o aplicativo?", size=16, weight="bold"),
                    ft.Container(height=20),
                    criar_botao("Sou Cliente (Quero pedir socorro)", lambda e: mostrar_tela("cadastro_cliente"), "#1976D2", "white", 350, 60),
                    ft.Container(height=10),
                    criar_botao("Sou Mecânico (Quero receber pedidos)", lambda e: mostrar_tela("cadastro_prestador"), "#E65100", "white", 350, 60),
                    ft.Container(height=30),
                    criar_botao("Voltar", lambda e: mostrar_tela("login"), "#CFD8DC", "black", 350, 45)
                ], horizontal_alignment="center")
            )
            page.add(cabecalho, corpo)

        elif nome_tela == "cadastro_cliente":
            txt_nome = ft.TextField(label="Seu Nome Completo", width=350)
            txt_telefone = ft.TextField(label="Telefone com DDD", width=350)
            txt_senha = ft.TextField(label="Crie uma Senha", password=True, width=350)
            lbl_aviso = ft.Text("", weight="bold")

            def salvar_cliente(e):
                if not txt_nome.value or not txt_telefone.value or not txt_senha.value:
                    lbl_aviso.value = "Preencha todos os campos!"
                    lbl_aviso.color = "red"
                elif db.telefone_existe(txt_telefone.value):
                    lbl_aviso.value = "Este telefone já está cadastrado!"
                    lbl_aviso.color = "red"
                else:
                    db.cadastrar_usuario_cliente(txt_nome.value, txt_telefone.value, txt_senha.value)
                    lbl_aviso.value = "Conta criada com sucesso! Volte e faça login."
                    lbl_aviso.color = "green"
                    txt_nome.value = txt_telefone.value = txt_senha.value = ""
                page.update()

            cabecalho = ft.Container(content=ft.Text("Cadastro de Cliente", color="white", size=20, weight="bold"), bgcolor="#0D47A1", padding=15, width=420)
            page.add(cabecalho, ft.Container(padding=20, content=ft.Column([
                txt_nome, txt_telefone, txt_senha, lbl_aviso,
                criar_botao("Cadastrar", salvar_cliente, "#4CAF50", "white", 350, 50),
                criar_botao("Voltar", lambda e: mostrar_tela("cadastro_escolha"), "#CFD8DC", "black", 350, 45)
            ], horizontal_alignment="center")))

        elif nome_tela == "cadastro_prestador":
            txt_nome = ft.TextField(label="Nome do Responsável", width=350)
            txt_oficina = ft.TextField(label="Nome da Oficina / Borracharia", width=350)
            txt_telefone = ft.TextField(label="Telefone (WhatsApp)", width=350)
            txt_senha = ft.TextField(label="Crie uma Senha", password=True, width=350)
            chk_24h = ft.Checkbox(label="Atendimento Plantão 24h", value=False)
            lbl_aviso = ft.Text("", weight="bold")

            def salvar_prestador(e):
                if not txt_nome.value or not txt_oficina.value or not txt_telefone.value or not txt_senha.value:
                    lbl_aviso.value = "Preencha todos os campos!"
                    lbl_aviso.color = "red"
                elif db.telefone_existe(txt_telefone.value):
                    lbl_aviso.value = "Este telefone já está cadastrado!"
                    lbl_aviso.color = "red"
                else:
                    db.cadastrar_usuario_prestador(txt_nome.value, txt_telefone.value, txt_senha.value, txt_oficina.value, chk_24h.value)
                    lbl_aviso.value = "Oficina cadastrada! Volte e faça login."
                    lbl_aviso.color = "green"
                    txt_nome.value = txt_oficina.value = txt_telefone.value = txt_senha.value = ""
                page.update()

            cabecalho = ft.Container(content=ft.Text("Cadastro de Oficina", color="white", size=20, weight="bold"), bgcolor="#E65100", padding=15, width=420)
            page.add(cabecalho, ft.Container(padding=20, content=ft.Column([
                txt_nome, txt_oficina, txt_telefone, txt_senha, chk_24h, lbl_aviso,
                criar_botao("Cadastrar Oficina", salvar_prestador, "#4CAF50", "white", 350, 50),
                criar_botao("Voltar", lambda e: mostrar_tela("cadastro_escolha"), "#CFD8DC", "black", 350, 45)
            ], horizontal_alignment="center")))

        elif nome_tela == "recuperar_senha":
            txt_telefone = ft.TextField(label="Digite seu Telefone cadastrado", width=350)
            txt_nova_senha = ft.TextField(label="Nova Senha", password=True, width=350)
            lbl_aviso = ft.Text("No app real, enviaremos um código. Aqui a senha será trocada direto abaixo:", color="grey", size=12, text_align="center", width=350)

            def salvar_nova_senha(e):
                if not db.telefone_existe(txt_telefone.value):
                    lbl_aviso.value = "Telefone não encontrado no sistema!"
                    lbl_aviso.color = "red"
                else:
                    db.redefinir_senha(txt_telefone.value, txt_nova_senha.value)
                    lbl_aviso.value = "Senha alterada com sucesso! Volte ao login."
                    lbl_aviso.color = "green"
                page.update()

            cabecalho = ft.Container(content=ft.Text("Recuperar Senha", color="white", size=20, weight="bold"), bgcolor="#0D47A1", padding=15, width=420)
            page.add(cabecalho, ft.Container(padding=20, content=ft.Column([
                lbl_aviso, ft.Container(height=10), txt_telefone, txt_nova_senha,
                criar_botao("Redefinir Senha", salvar_nova_senha, "#1976D2", "white", 350, 50),
                criar_botao("Voltar", lambda e: mostrar_tela("login"), "#CFD8DC", "black", 350, 45)
            ], horizontal_alignment="center")))

        elif nome_tela == "cliente_home":
            lat_cliente, lon_cliente = -19.9386, -43.9341
            lista_vitrine = ft.Column(spacing=12, scroll="auto", height=540)
            lbl_aviso_pedido = ft.Text("", color="green", weight="bold")

            def carregar_vitrine(filtro_24h=False):
                lista_vitrine.controls.clear()
                for p in db.get_prestadores_vitrine(lat_cliente, lon_cliente, filtro_24h):
                    aberto = p['aberto_agora']
                    
                    def solicitar_pedido(e, pid=p['id']):
                        criar_pedido(usuario_logado['id'], pid) 
                        lbl_aviso_pedido.value = "✅ Pedido enviado! Aguarde o mecânico aceitar."
                        page.update()

                    card = ft.Container(
                        padding=15, bgcolor="#F5F5F5", border_radius=10,
                        content=ft.Column([
                            ft.Text(f"🔧 {p['nome_oficina']}", weight="bold", size=17),
                            ft.Text(f"📍 {p['distancia_km']} km", color="grey"),
                            ft.Text(f"{'🟢 Aberto Agora' if aberto else '🔴 Fechado'} | ⭐ {p['nota_media']}", color="green" if aberto else "red", weight="bold"),
                            ft.Container(height=5),
                            criar_botao("Solicitar Socorro", solicitar_pedido, "#1976D2" if aberto else "grey", "white", 350, 42)
                        ])
                    )
                    lista_vitrine.controls.append(card)
                page.update()

            carregar_vitrine(False)
            cabecalho = ft.Container(bgcolor="#0D47A1", padding=15, width=420, content=ft.Row([criar_botao("⬅ Sair", lambda e: mostrar_tela("login"), "#1565C0", "white", 80, 38), ft.Text(f"Olá, {usuario_logado['nome']}!", color="white", weight="bold")]))
            controles_filtro = ft.Container(
                padding=12,
                content=ft.Column([
                    ft.Text("Precisa de ajuda urgente?", weight="bold"),
                    ft.Row([
                        criar_botao("🚨 Socorro 24h", lambda e: carregar_vitrine(True), "#D32F2F", "white", 180, 42, expandir=True),
                        criar_botao("Todas", lambda e: carregar_vitrine(False), "#CFD8DC", "black", 180, 42, expandir=True),
                    ]),
                    lbl_aviso_pedido,
                    ft.Divider(),
                    lista_vitrine
                ])
            )
            page.add(cabecalho, controles_filtro)

        elif nome_tela == "prestador_home":
            pid = usuario_logado['id']
            nome_oficina = usuario_logado['nome']
            lista_pedidos = ft.Column(spacing=12, scroll="auto", height=580)

            def carregar_pedidos():
                lista_pedidos.controls.clear()
                pedidos = buscar_pedidos_prestador(pid)
                
                if not pedidos:
                    lista_pedidos.controls.append(ft.Text("Nenhum pedido no momento. Mantenha o app aberto.", color="grey"))
                
                for p in pedidos:
                    status = p['status']
                    
                    def aceitar(e, ped_id=p['id']):
                        marcar_pedido_aceito(ped_id, pid)
                        carregar_pedidos()
                        
                    def abrir_whatsapp(e, tel=p['cliente_telefone'], ped_id=p['id']):
                        numero_limpo = str(tel).replace(" ", "").replace("-", "")
                        mensagem = urllib.parse.quote(f"Olá! Sou da oficina, falo sobre o pedido #{ped_id} no App.")
                        webbrowser.open(f"https://wa.me/55{numero_limpo}?text={mensagem}")
                        
                    def abrir_maps(e, lat=p['lat_cliente'], lon=p['lon_cliente']):
                        destino = f"{lat},{lon}" if lat and lon else "-19.9166,-43.9344"
                        webbrowser.open(f"https://www.google.com/maps/dir/?api=1&destination={destino}")

                    if status == 'pendente':
                        botoes = criar_botao("Aceitar Pedido (R$ 1.00)", aceitar, "#388E3C", "white", 350, 45)
                    else:
                        botoes = ft.Column([
                            criar_botao(f"📲 WhatsApp: {p['cliente_telefone']}", abrir_whatsapp, "#25D366", "white", 350, 42),
                            criar_botao("🗺️ Iniciar Rota (Google Maps)", abrir_maps, "#4285F4", "white", 350, 42)
                        ])

                    card = ft.Container(
                        padding=15, bgcolor="#FFF3E0" if status == 'pendente' else "#E8F5E9", border_radius=10,
                        content=ft.Column([
                            ft.Text(f"👤 Cliente: {p['cliente_nome']}", weight="bold", size=16),
                            ft.Text(f"Status: {status.upper()}", color="orange" if status == 'pendente' else "green", weight="bold"),
                            ft.Divider(),
                            botoes
                        ])
                    )
                    lista_pedidos.controls.append(card)
                page.update()

            carregar_pedidos()
            cabecalho = ft.Container(
                bgcolor="#E65100", padding=15, width=420, 
                content=ft.Column([
                    ft.Row([criar_botao("⬅ Sair", lambda e: mostrar_tela("login"), "#EF6C00", "white", 80, 38), ft.Text(nome_oficina, color="white", weight="bold")]),
                    ft.Text("Gestão de Pedidos e Plantão", color="white")
                ])
            )
            page.add(cabecalho, ft.Container(padding=15, content=ft.Column([criar_botao("🔄 Atualizar Pedidos", lambda e: carregar_pedidos(), "#FFB74D", "black", 380, 40), ft.Divider(), lista_pedidos])))

        elif nome_tela == "admin":
            cabecalho = ft.Container(content=ft.Text("Painel Admin", color="white", size=20, weight="bold"), bgcolor="#263238", padding=15, width=420)
            page.add(cabecalho, ft.Container(padding=20, content=ft.Column([ft.Text("Logado como Admin"), criar_botao("Sair", lambda e: mostrar_tela("login"), "#D32F2F", "white", 350, 45)])))

        page.update()

    mostrar_tela("login")

# --- BLOCO SUBSTITUÍDO PARA ATIVAR O PWA (WEB APP) ---
if __name__ == "__main__":
    porta_nuvem = int(os.getenv("PORT", 8550))
    
    # Executa o Flet passando 'main' diretamente
    if hasattr(ft, "run"):
        ft.run(
            main, 
            view=ft.AppView.WEB_BROWSER, 
            assets_dir="assets", 
            port=porta_nuvem, 
            host="0.0.0.0"
        )
    else:
        ft.app(
            main, 
            view=ft.AppView.WEB_BROWSER, 
            assets_dir="assets", 
            port=porta_nuvem, 
            host="0.0.0.0"
        )