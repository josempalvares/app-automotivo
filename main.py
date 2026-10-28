import flet as ft
import urllib.parse
import webbrowser
import database as db
import psycopg2.extras
import os

def main(page: ft.Page):
    page.title = "App Automotivo"
    try:
        page.window.width = 414
        page.window.height = 896
    except Exception:
        pass
    page.theme_mode = "light"
    page.padding = 0
    page.bgcolor = "#F4F6F9"

    def criar_botao(texto, acao_clique, cor_fundo="#0066FF", cor_texto="white", largura=350, altura=48, expandir=False):
        return ft.Container(
            content=ft.Row([ft.Text(texto, color=cor_texto, weight="w600", size=15)], alignment="center"),
            bgcolor=cor_fundo, width=largura, height=altura, border_radius=12, ink=True, on_click=acao_clique, expand=expandir, padding=10,
            shadow=ft.BoxShadow(blur_radius=6, color="#1A000000", offset=ft.Offset(0, 3))
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
            txt_telefone = ft.TextField(label="Telefone Cadastrado", width=350, border_radius=10, bgcolor="#FFFFFF", prefix_icon=ft.Icons.PHONE)
            txt_senha = ft.TextField(label="Senha", password=True, width=350, border_radius=10, bgcolor="#FFFFFF", prefix_icon=ft.Icons.LOCK)
            lbl_erro = ft.Text("", color="#D32F2F", weight="bold", size=13)

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

            topo_login = ft.Container(
                bgcolor="#0D47A1", padding=24, width=414,
                content=ft.Column([
                    ft.Text("Boas-vindas", color="white", size=24, weight="bold"),
                    ft.Text("Aceda à sua conta para solicitar assistência", color="#BBDEFB", size=14)
                ])
            )

            corpo = ft.Container(
                padding=24,
                content=ft.Column([
                    ft.Container(height=10),
                    ft.Row([
                        ft.Image(src="favicon.png", width=90, height=90, fit="contain")
                    ], alignment="center"),
                    ft.Container(height=10),
                    txt_telefone, txt_senha, lbl_erro,
                    ft.Container(height=10),
                    criar_botao("Entrar no Sistema", btn_login_click, "#0066FF", "white", 350, 48),
                    ft.Container(height=15),
                    ft.Row([
                        ft.TextButton("Esqueci minha senha", on_click=lambda e: mostrar_tela("recuperar_senha")),
                        ft.TextButton("Criar conta", on_click=lambda e: mostrar_tela("cadastro_escolha"))
                    ], alignment="spaceBetween", width=350)
                ], horizontal_alignment="center")
            )
            page.add(topo_login, corpo)

        elif nome_tela == "cadastro_escolha":
            topo = ft.Container(bgcolor="#0D47A1", padding=24, width=414, content=ft.Text("Criar Nova Conta", color="white", size=22, weight="bold"))
            corpo = ft.Container(
                padding=24,
                content=ft.Column([
                    ft.Text("Como deseja utilizar a plataforma?", size=16, weight="bold", color="#1E293B"),
                    ft.Container(height=15),
                    criar_botao("Sou Cliente (Pedir Socorro)", lambda e: mostrar_tela("cadastro_cliente"), "#0066FF", "white", 350, 56),
                    ft.Container(height=12),
                    criar_botao("Sou Mecânico / Oficina (Receber Pedidos)", lambda e: mostrar_tela("cadastro_prestador"), "#E65100", "white", 350, 56),
                    ft.Container(height=30),
                    criar_botao("Voltar ao Login", lambda e: mostrar_tela("login"), "#E2E8F0", "#334155", 350, 45)
                ], horizontal_alignment="center")
            )
            page.add(topo, corpo)

        elif nome_tela == "cadastro_cliente":
            txt_nome = ft.TextField(label="Nome Completo", width=350, border_radius=10, bgcolor="#FFFFFF")
            txt_telefone = ft.TextField(label="Telefone com DDD", width=350, border_radius=10, bgcolor="#FFFFFF")
            txt_senha = ft.TextField(label="Senha de Acesso", password=True, width=350, border_radius=10, bgcolor="#FFFFFF")
            lbl_aviso = ft.Text("", weight="bold", size=13)

            def salvar_cliente(e):
                if not txt_nome.value or not txt_telefone.value or not txt_senha.value:
                    lbl_aviso.value = "Preencha todos os campos obrigatórios!"
                    lbl_aviso.color = "#D32F2F"
                elif db.telefone_existe(txt_telefone.value):
                    lbl_aviso.value = "Este telefone já está registado!"
                    lbl_aviso.color = "#D32F2F"
                else:
                    db.cadastrar_usuario_cliente(txt_nome.value, txt_telefone.value, txt_senha.value)
                    lbl_aviso.value = "Conta criada com sucesso! Faça login."
                    lbl_aviso.color = "#388E3C"
                    txt_nome.value = txt_telefone.value = txt_senha.value = ""
                page.update()

            topo = ft.Container(bgcolor="#0D47A1", padding=24, width=414, content=ft.Text("Registo de Cliente", color="white", size=22, weight="bold"))
            page.add(topo, ft.Container(padding=24, content=ft.Column([
                txt_nome, txt_telefone, txt_senha, lbl_aviso,
                ft.Container(height=10),
                criar_botao("Finalizar Registo", salvar_cliente, "#388E3C", "white", 350, 48),
                criar_botao("Voltar", lambda e: mostrar_tela("cadastro_escolha"), "#E2E8F0", "#334155", 350, 45)
            ], horizontal_alignment="center")))

        elif nome_tela == "cadastro_prestador":
            txt_nome = ft.TextField(label="Nome do Responsável", width=350, border_radius=10, bgcolor="#FFFFFF")
            txt_oficina = ft.TextField(label="Nome da Oficina / Borracharia", width=350, border_radius=10, bgcolor="#FFFFFF")
            txt_telefone = ft.TextField(label="Telefone (WhatsApp)", width=350, border_radius=10, bgcolor="#FFFFFF")
            txt_senha = ft.TextField(label="Senha de Acesso", password=True, width=350, border_radius=10, bgcolor="#FFFFFF")
            chk_24h = ft.Checkbox(label="Atendimento Plantão 24h", value=False)
            lbl_aviso = ft.Text("", weight="bold", size=13)

            def salvar_prestador(e):
                if not txt_nome.value or not txt_oficina.value or not txt_telefone.value or not txt_senha.value:
                    lbl_aviso.value = "Preencha todos os campos!"
                    lbl_aviso.color = "#D32F2F"
                elif db.telefone_existe(txt_telefone.value):
                    lbl_aviso.value = "Este telefone já está registado!"
                    lbl_aviso.color = "#D32F2F"
                else:
                    db.cadastrar_usuario_prestador(txt_nome.value, txt_telefone.value, txt_senha.value, txt_oficina.value, chk_24h.value)
                    lbl_aviso.value = "Oficina registada com sucesso! Faça login."
                    lbl_aviso.color = "#388E3C"
                    txt_nome.value = txt_oficina.value = txt_telefone.value = txt_senha.value = ""
                page.update()

            topo = ft.Container(bgcolor="#E65100", padding=24, width=414, content=ft.Text("Registo de Oficina / Prestador", color="white", size=22, weight="bold"))
            page.add(topo, ft.Container(padding=24, content=ft.Column([
                txt_nome, txt_oficina, txt_telefone, txt_senha, chk_24h, lbl_aviso,
                ft.Container(height=10),
                criar_botao("Registar Oficina", salvar_prestador, "#388E3C", "white", 350, 48),
                criar_botao("Voltar", lambda e: mostrar_tela("cadastro_escolha"), "#E2E8F0", "#334155", 350, 45)
            ], horizontal_alignment="center")))

        elif nome_tela == "recuperar_senha":
            txt_telefone = ft.TextField(label="Telefone Registado", width=350, border_radius=10, bgcolor="#FFFFFF")
            txt_nova_senha = ft.TextField(label="Nova Senha", password=True, width=350, border_radius=10, bgcolor="#FFFFFF")
            lbl_aviso = ft.Text("", color="grey", size=13, text_align="center", width=350)

            def salvar_nova_senha(e):
                if not db.telefone_existe(txt_telefone.value):
                    lbl_aviso.value = "Telefone não encontrado no sistema!"
                    lbl_aviso.color = "#D32F2F"
                else:
                    db.redefinir_senha(txt_telefone.value, txt_nova_senha.value)
                    lbl_aviso.value = "Senha alterada com sucesso! Volte ao login."
                    lbl_aviso.color = "#388E3C"
                page.update()

            topo = ft.Container(bgcolor="#0D47A1", padding=24, width=414, content=ft.Text("Recuperar Palavra-passe", color="white", size=22, weight="bold"))
            page.add(topo, ft.Container(padding=24, content=ft.Column([
                txt_telefone, txt_nova_senha, lbl_aviso,
                ft.Container(height=10),
                criar_botao("Atualizar Senha", salvar_nova_senha, "#0066FF", "white", 350, 48),
                criar_botao("Voltar", lambda e: mostrar_tela("login"), "#E2E8F0", "#334155", 350, 45)
            ], horizontal_alignment="center")))

        elif nome_tela == "cliente_home":
            lat_cliente, lon_cliente = -19.9386, -43.9341
            lista_vitrine = ft.Column(spacing=16, scroll="auto", height=450)
            lbl_aviso_pedido = ft.Text("", color="#2E7D32", weight="bold", size=13)

            imagens_demo = ["mecanico_destaque.jpg", "reboque_socorro.jpg", "troca_pneu.jpg"]

            def carregar_vitrine(filtro_24h=False):
                lista_vitrine.controls.clear()
                prestadores = db.get_prestadores_vitrine(lat_cliente, lon_cliente, filtro_24h)
                
                if not prestadores:
                    lista_vitrine.controls.append(ft.Text("Nenhum profissional disponível no momento.", color="#64748B", size=14))

                for i, p in enumerate(prestadores):
                    aberto = p['aberto_agora']
                    img_src = imagens_demo[i % len(imagens_demo)] 
                    
                    def solicitar_pedido(e, pid=p['id']):
                        criar_pedido(usuario_logado['id'], pid) 
                        lbl_aviso_pedido.value = "✅ Pedido enviado com sucesso! Aguarde aceitação."
                        page.update()

                    card = ft.Container(
                        bgcolor="white",
                        border_radius=16,
                        shadow=ft.BoxShadow(blur_radius=10, color="#14000000", offset=ft.Offset(0, 4)),
                        content=ft.Column(spacing=0, controls=[
                            ft.Stack([
                                ft.Image(
                                    src=img_src, 
                                    height=140, 
                                    width=400, 
                                    fit="cover", 
                                    border_radius=ft.BorderRadius(top_left=16, top_right=16, bottom_left=0, bottom_right=0)
                                ),
                                ft.Container(
                                    content=ft.Text("ABERTO AGORA" if aberto else "FECHADO", color="white", size=11, weight="bold"),
                                    bgcolor="#2E7D32" if aberto else "#C62828",
                                    padding=ft.Padding(top=6, bottom=6, left=12, right=12),
                                    border_radius=20,
                                    margin=12
                                )
                            ]),
                            ft.Container(
                                padding=16,
                                content=ft.Column(spacing=8, controls=[
                                    ft.Text(p['nome_oficina'], weight="bold", size=18, color="#1E293B"),
                                    ft.Row([
                                        ft.Icon(ft.Icons.LOCATION_ON, size=16, color="#64748B"),
                                        ft.Text(f"{p['distancia_km']} km de distância", color="#64748B", size=13),
                                    ]),
                                    ft.Row([
                                        ft.Icon(ft.Icons.STAR, size=16, color="#F59E0B"),
                                        ft.Text(f"{p['nota_media']}", weight="bold", size=14, color="#1E293B"),
                                        ft.Text(" • ", color="#CBD5E1"),
                                        ft.Text("Disponível" if aberto else "Indisponível", color="#2E7D32" if aberto else "#C62828", size=13, weight="w600")
                                    ]),
                                    ft.Container(height=4),
                                    criar_botao("Solicitar Socorro Imediato", solicitar_pedido, "#0066FF" if aberto else "#94A3B8", "white", 350, 44)
                                ])
                            )
                        ])
                    )
                    lista_vitrine.controls.append(card)
                page.update()

            carregar_vitrine(False)
            
            cabecalho = ft.Container(
                bgcolor="white", 
                padding=ft.Padding(top=16, left=20, right=20, bottom=16), 
                width=414, 
                shadow=ft.BoxShadow(blur_radius=5, color="#0A000000", offset=ft.Offset(0, 2)),
                content=ft.Row([
                    ft.Row([
                        ft.Image(src="favicon.png", width=36, height=36, fit="contain"),
                        ft.Text(f"Olá, {usuario_logado['nome'].split()[0]}!", color="#1E293B", weight="bold", size=18)
                    ], spacing=10),
                    ft.IconButton(icon=ft.Icons.LOGOUT, icon_color="#64748B", on_click=lambda e: mostrar_tela("login"))
                ], alignment="spaceBetween")
            )
            
            banner_promocional = ft.Container(
                margin=ft.Padding(top=16, left=16, right=16, bottom=0),
                padding=20,
                bgcolor="#0066FF",
                border_radius=16,
                content=ft.Row([
                    ft.Column([
                        ft.Text("Precisa de reboque?", color="white", weight="bold", size=16),
                        ft.Text("Plantão 24h ativo em sua região.", color="#E0F2FE", size=13),
                    ], expand=True),
                    ft.Icon(ft.Icons.LOCAL_SHIPPING, color="white", size=36)
                ])
            )

            filtros_rapidos = ft.Container(
                padding=ft.Padding(top=16, left=16, right=16, bottom=8),
                content=ft.Column([
                    ft.Text("Serviços Disponíveis", weight="bold", size=18, color="#1E293B"),
                    ft.Container(height=8),
                    ft.Row([
                        criar_botao("🚨 Plantão 24h", lambda e: carregar_vitrine(True), "#DC2626", "white", 175, 42, expandir=True),
                        criar_botao("Todos os Serviços", lambda e: carregar_vitrine(False), "white", "#0066FF", 175, 42, expandir=True),
                    ], spacing=10),
                    lbl_aviso_pedido,
                ])
            )

            # Barra de navegação inferior profissional
            nav_bar = ft.Container(
                bgcolor="white",
                padding=12,
                width=414,
                shadow=ft.BoxShadow(blur_radius=8, color="#1A000000", offset=ft.Offset(0, -2)),
                content=ft.Row([
                    ft.Column([ft.Icon(ft.Icons.HOME, color="#0066FF", size=22), ft.Text("Início", size=11, color="#0066FF", weight="bold")], horizontal_alignment="center", expand=True),
                    ft.Column([ft.Icon(ft.Icons.SEARCH, color="#94A3B8", size=22), ft.Text("Buscar", size=11, color="#94A3B8")], horizontal_alignment="center", expand=True),
                    ft.Column([ft.Icon(ft.Icons.RECEIPT_LONG, color="#94A3B8", size=22), ft.Text("Pedidos", size=11, color="#94A3B8")], horizontal_alignment="center", expand=True),
                    ft.Column([ft.Icon(ft.Icons.PERSON, color="#94A3B8", size=22), ft.Text("Perfil", size=11, color="#94A3B8")], horizontal_alignment="center", expand=True),
                ], alignment="spaceAround")
            )
            
            conteudo_principal = ft.Column([cabecalho, banner_promocional, filtros_rapidos, ft.Container(content=lista_vitrine, padding=ft.Padding(left=16, right=16, bottom=16))], spacing=0, expand=True)
            page.add(conteudo_principal, nav_bar)

        elif nome_tela == "prestador_home":
            pid = usuario_logado['id']
            nome_oficina = usuario_logado['nome']
            lista_pedidos = ft.Column(spacing=12, scroll="auto", height=600)

            def carregar_pedidos():
                lista_pedidos.controls.clear()
                pedidos = buscar_pedidos_prestador(pid)
                
                if not pedidos:
                    lista_pedidos.controls.append(ft.Text("Sem pedidos no momento. Mantenha o app aberto.", color="#64748B"))
                
                for p in pedidos:
                    status = p['status']
                    
                    def aceitar(e, ped_id=p['id']):
                        marcar_pedido_aceito(ped_id, pid)
                        carregar_pedidos()
                        
                    def abrir_whatsapp(e, tel=p['cliente_telefone'], ped_id=p['id']):
                        numero_limpo = str(tel).replace(" ", "").replace("-", "")
                        mensagem = urllib.parse.quote(f"Olá! Sou da oficina, falo sobre o pedido #{ped_id} no App Automotivo.")
                        webbrowser.open(f"https://wa.me/55{numero_limpo}?text={mensagem}")
                        
                    def abrir_maps(e, lat=p['lat_cliente'], lon=p['lon_cliente']):
                        destino = f"{lat},{lon}" if lat and lon else "-19.9166,-43.9344"
                        webbrowser.open(f"https://www.google.com/maps/dir/?api=1&destination={destino}")

                    if status == 'pendente':
                        botoes = criar_botao("Aceitar Pedido (R$ 1.00)", aceitar, "#2E7D32", "white", 350, 45)
                    else:
                        botoes = ft.Column([
                            criar_botao(f"📲 WhatsApp: {p['cliente_telefone']}", abrir_whatsapp, "#25D366", "white", 350, 42),
                            criar_botao("🗺️ Abrir Rota (Google Maps)", abrir_maps, "#0066FF", "white", 350, 42)
                        ], spacing=8)

                    card = ft.Container(
                        padding=16, bgcolor="#FFFBEB" if status == 'pendente' else "#F0FDF4", border_radius=12,
                        shadow=ft.BoxShadow(blur_radius=6, color="#0A000000", offset=ft.Offset(0, 2)),
                        content=ft.Column([
                            ft.Row([
                                ft.Text(f"👤 Cliente: {p['cliente_nome']}", weight="bold", size=16, color="#1E293B"),
                                ft.Text(f"{status.upper()}", color="#D97706" if status == 'pendente' else "#16A34A", weight="bold", size=12)
                            ], alignment="spaceBetween"),
                            ft.Divider(),
                            botoes
                        ])
                    )
                    lista_pedidos.controls.append(card)
                page.update()

            carregar_pedidos()
            cabecalho = ft.Container(
                bgcolor="#E65100", padding=20, width=414, 
                content=ft.Column([
                    ft.Row([ft.Text(nome_oficina, color="white", weight="bold", size=18), ft.IconButton(icon=ft.Icons.LOGOUT, icon_color="white", on_click=lambda e: mostrar_tela("login"))], alignment="spaceBetween"),
                    ft.Text("Painel de Gestão de Pedidos e Plantão", color="#FFE0B2", size=13)
                ])
            )
            page.add(cabecalho, ft.Container(padding=16, content=ft.Column([criar_botao("🔄 Atualizar Pedidos", lambda e: carregar_pedidos(), "#FFB74D", "#1E293B", 380, 42), ft.Container(height=10), lista_pedidos])))

        elif nome_tela == "admin":
            cabecalho = ft.Container(content=ft.Text("Painel Administrativo", color="white", size=20, weight="bold"), bgcolor="#1E293B", padding=20, width=414)
            page.add(cabecalho, ft.Container(padding=24, content=ft.Column([ft.Text("Sessão Administrativa Ativa", color="#64748B"), criar_botao("Terminar Sessão", lambda e: mostrar_tela("login"), "#DC2626", "white", 350, 45)])))

        page.update()

    mostrar_tela("login")

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8000))
    
    if hasattr(ft, "run"):
        ft.run(main, view=ft.AppView.WEB_BROWSER, port=porta, assets_dir="assets")
    else:
        ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=porta, assets_dir="assets")