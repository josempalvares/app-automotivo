import flet as ft
import urllib.parse
import webbrowser
import database as db
import psycopg2.extras
import os

def main(page: ft.Page):
    page.title = "App Automotivo"
    page.theme_mode = "light"
    page.padding = 0
    page.spacing = 0
    page.bgcolor = "#E2E8F0"

    try:
        page.window.width = 420
        page.window.height = 860
    except Exception:
        pass

    def criar_moldura_mobile(conteudo_principal, barra_inferior=None):
        coluna_interna = [ft.Container(content=conteudo_principal, expand=True)]
        if barra_inferior:
            coluna_interna.append(barra_inferior)

        return ft.Row(
            alignment="center",
            vertical_alignment="stretch",
            expand=True,
            controls=[
                ft.Container(
                    width=430,
                    bgcolor="#F8FAFC",
                    shadow=ft.BoxShadow(blur_radius=20, color="#1A000000", offset=ft.Offset(0, 0)),
                    content=ft.Column(spacing=0, expand=True, controls=coluna_interna)
                )
            ]
        )

    def criar_input(label_texto, icone=None, senha=False):
        return ft.TextField(
            label=label_texto,
            password=senha,
            prefix_icon=icone,
            bgcolor="#FFFFFF",
            filled=True,
            border_radius=12,
            content_padding=ft.Padding(left=16, right=16, top=16, bottom=16),
            text_size=14
        )

    def criar_botao(texto, acao_clique, cor_fundo="#0066FF", cor_texto="white", altura=48, expandir=False):
        return ft.Container(
            content=ft.Row([ft.Text(texto, color=cor_texto, weight="w600", size=15)], alignment="center"),
            bgcolor=cor_fundo,
            height=altura,
            border_radius=12,
            ink=True,
            on_click=acao_clique,
            expand=expandir,
            padding=ft.Padding(left=16, right=16, top=0, bottom=0)
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
            txt_telefone = criar_input("Telefone Cadastrado", icone=ft.Icons.PHONE)
            txt_senha = criar_input("Sua Senha", icone=ft.Icons.LOCK, senha=True)
            lbl_erro = ft.Text("", color="#DC2626", weight="w600", size=13)

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
                    lbl_erro.value = "Telefone ou senha incorretos."
                    page.update()

            conteudo = ft.Container(
                bgcolor="#FFFFFF",
                expand=True,
                padding=ft.Padding(left=28, right=28, top=45, bottom=24),
                content=ft.Column(
                    scroll="auto",
                    horizontal_alignment="center",
                    controls=[
                        ft.Image(
                            src="logo.svg",
                            width=115,
                            height=115,
                            fit="contain"
                        ),
                        ft.Container(height=14),
                        ft.Text("Boas-vindas", size=26, weight="bold", color="#0F172A"),
                        ft.Text("Socorro automotivo rápido na palma da mão", size=14, color="#64748B", text_align="center"),
                        ft.Container(height=28),
                        txt_telefone,
                        ft.Container(height=12),
                        txt_senha,
                        ft.Container(height=6),
                        lbl_erro,
                        ft.Container(height=12),
                        ft.Row([criar_botao("Entrar na Conta", btn_login_click, "#0066FF", "white", 50, expandir=True)]),
                        ft.Container(height=16),
                        ft.Row([
                            ft.TextButton("Esqueci a senha", on_click=lambda e: mostrar_tela("recuperar_senha")),
                            ft.TextButton("Criar nova conta", on_click=lambda e: mostrar_tela("cadastro_escolha"))
                        ], alignment="spaceBetween")
                    ]
                )
            )
            page.add(criar_moldura_mobile(conteudo))

        elif nome_tela == "cadastro_escolha":
            conteudo = ft.Container(
                bgcolor="#FFFFFF",
                expand=True,
                padding=28,
                content=ft.Column([
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color="#0F172A", on_click=lambda e: mostrar_tela("login")),
                        ft.Text("Criar Nova Conta", size=20, weight="bold", color="#0F172A")
                    ]),
                    ft.Container(height=20),
                    ft.Text("Como você deseja usar a plataforma?", size=16, color="#475569"),
                    ft.Container(height=20),
                    ft.Container(
                        padding=20,
                        border_radius=16,
                        bgcolor="#F8FAFC",
                        border=ft.Border.all(1, "#E2E8F0"),
                        ink=True,
                        on_click=lambda e: mostrar_tela("cadastro_cliente"),
                        content=ft.Row([
                            ft.Container(padding=12, bgcolor="#DBEAFE", border_radius=12, content=ft.Icon(ft.Icons.DIRECTIONS_CAR, color="#0066FF", size=28)),
                            ft.Column([
                                ft.Text("Sou Motorista / Cliente", weight="bold", size=16, color="#0F172A"),
                                ft.Text("Quero solicitar reboque ou socorro", size=13, color="#64748B")
                            ], spacing=2, expand=True),
                            ft.Icon(ft.Icons.CHEVRON_RIGHT, color="#94A3B8")
                        ], spacing=15)
                    ),
                    ft.Container(height=14),
                    ft.Container(
                        padding=20,
                        border_radius=16,
                        bgcolor="#F8FAFC",
                        border=ft.Border.all(1, "#E2E8F0"),
                        ink=True,
                        on_click=lambda e: mostrar_tela("cadastro_prestador"),
                        content=ft.Row([
                            ft.Container(padding=12, bgcolor="#FFEDD5", border_radius=12, content=ft.Icon(ft.Icons.BUILD, color="#EA580C", size=28)),
                            ft.Column([
                                ft.Text("Sou Oficina / Prestador", weight="bold", size=16, color="#0F172A"),
                                ft.Text("Quero atender clientes na minha região", size=13, color="#64748B")
                            ], spacing=2, expand=True),
                            ft.Icon(ft.Icons.CHEVRON_RIGHT, color="#94A3B8")
                        ], spacing=15)
                    )
                ])
            )
            page.add(criar_moldura_mobile(conteudo))

        elif nome_tela == "cadastro_cliente":
            txt_nome = criar_input("Nome Completo", icone=ft.Icons.PERSON)
            txt_telefone = criar_input("Telefone com DDD", icone=ft.Icons.PHONE)
            txt_senha = criar_input("Crie uma Senha", icone=ft.Icons.LOCK, senha=True)
            lbl_aviso = ft.Text("", weight="w600", size=13)

            def salvar_cliente(e):
                if not txt_nome.value or not txt_telefone.value or not txt_senha.value:
                    lbl_aviso.value = "Preencha todos os campos!"
                    lbl_aviso.color = "#DC2626"
                elif db.telefone_existe(txt_telefone.value):
                    lbl_aviso.value = "Este telefone já está cadastrado!"
                    lbl_aviso.color = "#DC2626"
                else:
                    db.cadastrar_usuario_cliente(txt_nome.value, txt_telefone.value, txt_senha.value)
                    lbl_aviso.value = "Conta criada com sucesso! Volte ao login."
                    lbl_aviso.color = "#16A34A"
                    txt_nome.value = txt_telefone.value = txt_senha.value = ""
                page.update()

            conteudo = ft.Container(
                bgcolor="#FFFFFF", expand=True, padding=28,
                content=ft.Column([
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color="#0F172A", on_click=lambda e: mostrar_tela("cadastro_escolha")),
                        ft.Text("Cadastro de Cliente", size=20, weight="bold", color="#0F172A")
                    ]),
                    ft.Container(height=15),
                    txt_nome, ft.Container(height=10),
                    txt_telefone, ft.Container(height=10),
                    txt_senha, ft.Container(height=10),
                    lbl_aviso,
                    ft.Row([criar_botao("Concluir Cadastro", salvar_cliente, "#0066FF", "white", 50, expandir=True)])
                ])
            )
            page.add(criar_moldura_mobile(conteudo))

        elif nome_tela == "cadastro_prestador":
            txt_nome = criar_input("Nome do Responsável", icone=ft.Icons.PERSON)
            txt_oficina = criar_input("Nome da Oficina / Reboque", icone=ft.Icons.STORE)
            txt_telefone = criar_input("WhatsApp com DDD", icone=ft.Icons.PHONE)
            txt_senha = criar_input("Crie uma Senha", icone=ft.Icons.LOCK, senha=True)
            chk_24h = ft.Checkbox(label="Atendo em Plantão 24 Horas", value=False)
            lbl_aviso = ft.Text("", weight="w600", size=13)

            def salvar_prestador(e):
                if not txt_nome.value or not txt_oficina.value or not txt_telefone.value or not txt_senha.value:
                    lbl_aviso.value = "Preencha todos os campos!"
                    lbl_aviso.color = "#DC2626"
                elif db.telefone_existe(txt_telefone.value):
                    lbl_aviso.value = "Este telefone já está cadastrado!"
                    lbl_aviso.color = "#DC2626"
                else:
                    db.cadastrar_usuario_prestador(txt_nome.value, txt_telefone.value, txt_senha.value, txt_oficina.value, chk_24h.value)
                    lbl_aviso.value = "Oficina cadastrada com sucesso! Faça login."
                    lbl_aviso.color = "#16A34A"
                    txt_nome.value = txt_oficina.value = txt_telefone.value = txt_senha.value = ""
                page.update()

            conteudo = ft.Container(
                bgcolor="#FFFFFF", expand=True, padding=28,
                content=ft.Column(scroll="auto", controls=[
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color="#0F172A", on_click=lambda e: mostrar_tela("cadastro_escolha")),
                        ft.Text("Cadastro de Parceiro", size=20, weight="bold", color="#0F172A")
                    ]),
                    ft.Container(height=15),
                    txt_nome, ft.Container(height=10),
                    txt_oficina, ft.Container(height=10),
                    txt_telefone, ft.Container(height=10),
                    txt_senha, ft.Container(height=10),
                    chk_24h, lbl_aviso,
                    ft.Row([criar_botao("Cadastrar Oficina", salvar_prestador, "#EA580C", "white", 50, expandir=True)])
                ])
            )
            page.add(criar_moldura_mobile(conteudo))

        elif nome_tela == "recuperar_senha":
            txt_telefone = criar_input("Telefone Cadastrado", icone=ft.Icons.PHONE)
            txt_nova_senha = criar_input("Digite a Nova Senha", icone=ft.Icons.LOCK, senha=True)
            lbl_aviso = ft.Text("", size=13, weight="w600")

            def salvar_nova_senha(e):
                if not db.telefone_existe(txt_telefone.value):
                    lbl_aviso.value = "Telefone não encontrado!"
                    lbl_aviso.color = "#DC2626"
                else:
                    db.redefinir_senha(txt_telefone.value, txt_nova_senha.value)
                    lbl_aviso.value = "Senha atualizada com sucesso!"
                    lbl_aviso.color = "#16A34A"
                page.update()

            conteudo = ft.Container(
                bgcolor="#FFFFFF", expand=True, padding=28,
                content=ft.Column([
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color="#0F172A", on_click=lambda e: mostrar_tela("login")),
                        ft.Text("Recuperar Senha", size=20, weight="bold", color="#0F172A")
                    ]),
                    ft.Container(height=15),
                    txt_telefone, ft.Container(height=10),
                    txt_nova_senha, ft.Container(height=10),
                    lbl_aviso,
                    ft.Row([criar_botao("Redefinir Senha", salvar_nova_senha, "#0066FF", "white", 50, expandir=True)])
                ])
            )
            page.add(criar_moldura_mobile(conteudo))

        elif nome_tela == "cliente_home":
            lat_cliente, lon_cliente = -19.9386, -43.9341
            lista_vitrine = ft.Column(spacing=16)
            lbl_titulo_secao = ft.Text("Oficinas e Socorro", weight="bold", size=19, color="#0F172A")
            lbl_aviso_pedido = ft.Container(visible=False)
            txt_busca = ft.TextField(
                hint_text="O que você precisa hoje?",
                prefix_icon=ft.Icons.SEARCH,
                bgcolor="#F1F5F9",
                filled=True,
                border_radius=12,
                content_padding=ft.Padding(left=14, right=14, top=12, bottom=12),
                text_size=14,
                on_change=lambda e: carregar_vitrine(filtro_atual[0], e.control.value)
            )

            filtro_atual = [False]
            imagens_demo = ["mecanico_destaque.jpg", "reboque_socorro.jpg", "troca_pneu.jpg"]

            def criar_card_categoria(icone, cor_icone, titulo, sub, acao):
                return ft.Container(
                    expand=True,
                    on_click=acao,
                    ink=True,
                    content=ft.Column(
                        horizontal_alignment="center",
                        spacing=6,
                        controls=[
                            ft.Container(
                                width=68,
                                height=68,
                                bgcolor="#FFFFFF",
                                border_radius=14,
                                border=ft.Border.all(1, "#E2E8F0"),
                                alignment=ft.Alignment(0, 0),
                                shadow=ft.BoxShadow(blur_radius=6, color="#08000000", offset=ft.Offset(0, 2)),
                                content=ft.Icon(icone, color=cor_icone, size=28)
                            ),
                            ft.Text(titulo, size=12, weight="w600", color="#334155", text_align="center"),
                            ft.Text(sub, size=11, color="#64748B", text_align="center")
                        ]
                    )
                )

            def carregar_vitrine(filtro_24h=False, termo_busca=""):
                filtro_atual[0] = filtro_24h
                lbl_titulo_secao.value = "Plantão 24 Horas" if filtro_24h else "Oficinas e Socorro"
                lista_vitrine.controls.clear()
                
                prestadores = db.get_prestadores_vitrine(lat_cliente, lon_cliente, filtro_24h)
                if termo_busca:
                    prestadores = [p for p in prestadores if termo_busca.lower() in p['nome_oficina'].lower()]

                if not prestadores:
                    lista_vitrine.controls.append(
                        ft.Container(
                            padding=24, bgcolor="#FFFFFF", border_radius=16,
                            content=ft.Text("Nenhum prestador encontrado para este filtro.", color="#64748B", text_align="center")
                        )
                    )

                for i, p in enumerate(prestadores):
                    aberto = p['aberto_agora']
                    img_src = imagens_demo[i % len(imagens_demo)] 
                    
                    def solicitar_pedido(e, pid=p['id'], nome_of=p['nome_oficina']):
                        criar_pedido(usuario_logado['id'], pid)
                        lbl_aviso_pedido.visible = True
                        lbl_aviso_pedido.content = ft.Container(
                            padding=14, bgcolor="#DCFCE7", border_radius=12, border=ft.Border.all(1, "#86EFAC"),
                            content=ft.Row([
                                ft.Icon(ft.Icons.CHECK_CIRCLE, color="#16A34A", size=20),
                                ft.Text(f"Pedido enviado para {nome_of}! Aguarde o aceite.", color="#15803D", weight="w600", size=13, expand=True)
                            ])
                        )
                        page.update()

                    card_oficina = ft.Container(
                        bgcolor="#FFFFFF",
                        border_radius=16,
                        border=ft.Border.all(1, "#E2E8F0"),
                        shadow=ft.BoxShadow(blur_radius=12, color="#0D000000", offset=ft.Offset(0, 4)),
                        content=ft.Column(spacing=0, controls=[
                            ft.Stack([
                                ft.Image(
                                    src=img_src, 
                                    height=155, 
                                    width=430, 
                                    fit="cover", 
                                    border_radius=ft.BorderRadius(top_left=15, top_right=15, bottom_left=0, bottom_right=0)
                                ),
                                ft.Container(
                                    content=ft.Row([
                                        ft.Container(width=7, height=7, border_radius=4, bgcolor="#FFFFFF"),
                                        ft.Text("ABERTO AGORA" if aberto else "FECHADO", color="white", size=10, weight="bold")
                                    ], spacing=5, tight=True),
                                    bgcolor="#16A34A" if aberto else "#DC2626",
                                    padding=ft.Padding(top=5, bottom=5, left=10, right=10),
                                    border_radius=20,
                                    margin=12
                                )
                            ]),
                            ft.Container(
                                padding=16,
                                content=ft.Column(spacing=10, controls=[
                                    ft.Row([
                                        ft.Text(p['nome_oficina'], weight="bold", size=17, color="#0F172A", expand=True),
                                        ft.Container(
                                            bgcolor="#FEF3C7", padding=ft.Padding(left=8, right=8, top=4, bottom=4), border_radius=8,
                                            content=ft.Row([
                                                ft.Icon(ft.Icons.STAR, size=15, color="#D97706"),
                                                ft.Text(f"{p['nota_media']}", weight="bold", size=13, color="#92400E")
                                            ], spacing=3)
                                        )
                                    ], alignment="spaceBetween"),
                                    ft.Row([
                                        ft.Icon(ft.Icons.LOCATION_ON, size=16, color="#64748B"),
                                        ft.Text(f"{p['distancia_km']} km de você", color="#64748B", size=13),
                                        ft.Text("•", color="#CBD5E1"),
                                        ft.Text("Atendimento Rápido", color="#0066FF", size=13, weight="w500")
                                    ], spacing=6),
                                    ft.Container(height=2),
                                    ft.Row([
                                        criar_botao(
                                            "Solicitar Socorro Imediato",
                                            solicitar_pedido,
                                            "#0066FF" if aberto else "#94A3B8",
                                            "white",
                                            44,
                                            expandir=True
                                        )
                                    ])
                                ])
                            )
                        ])
                    )
                    lista_vitrine.controls.append(card_oficina)
                page.update()

            carregar_vitrine(False)

            primeiro_nome = usuario_logado['nome'].split()[0]

            bloco_topo_branco = ft.Container(
                bgcolor="#FFFFFF",
                padding=ft.Padding(left=20, right=20, top=18, bottom=22),
                content=ft.Column(spacing=16, controls=[
                    ft.Row([
                        ft.Row([
                            ft.Image(src="logo.svg", width=44, height=44, fit="contain"),
                            ft.Column([
                                ft.Text("Boas-vindas,", size=12, color="#64748B"),
                                ft.Text(f"{primeiro_nome}!", size=20, weight="bold", color="#0F172A")
                            ], spacing=0)
                        ], spacing=12),
                        ft.IconButton(icon=ft.Icons.LOGOUT, icon_color="#64748B", tooltip="Sair", on_click=lambda e: mostrar_tela("login"))
                    ], alignment="spaceBetween"),
                    txt_busca,
                    ft.Row(
                        alignment="spaceBetween",
                        vertical_alignment="start",
                        controls=[
                            criar_card_categoria(ft.Icons.EMERGENCY, "#DC2626", "Plantão", "24 Horas", lambda e: carregar_vitrine(True)),
                            criar_card_categoria(ft.Icons.CAR_REPAIR, "#0066FF", "Mecânica", "Geral", lambda e: carregar_vitrine(False)),
                            criar_card_categoria(ft.Icons.LOCAL_SHIPPING, "#D97706", "Reboque", "Guincho", lambda e: carregar_vitrine(True)),
                            criar_card_categoria(ft.Icons.BUILD_CIRCLE, "#16A34A", "Pneus e", "Bateria", lambda e: carregar_vitrine(False)),
                        ]
                    )
                ])
            )

            banner_azul = ft.Container(
                margin=ft.Padding(left=20, right=20, top=18, bottom=10),
                padding=22,
                border_radius=16,
                gradient=ft.LinearGradient(
                    begin=ft.Alignment(-1, -1),
                    end=ft.Alignment(1, 1),
                    colors=["#0052CC", "#0066FF", "#2684FF"]
                ),
                shadow=ft.BoxShadow(blur_radius=12, color="#330066FF", offset=ft.Offset(0, 4)),
                on_click=lambda e: carregar_vitrine(True),
                ink=True,
                content=ft.Row([
                    ft.Column([
                        ft.Text("Emergência na via?", color="white", weight="bold", size=18),
                        ft.Text("Acione o plantão 24h mais próximo\ne acompanhe o atendimento.", color="#E0F2FE", size=13),
                    ], spacing=6, expand=True),
                    ft.Container(
                        width=46, height=46, border_radius=23, bgcolor="#0043A6",
                        alignment=ft.Alignment(0, 0),
                        content=ft.Icon(ft.Icons.ARROW_FORWARD, color="white", size=22)
                    )
                ], vertical_alignment="center")
            )

            secao_vitrine = ft.Container(
                padding=ft.Padding(left=20, right=20, top=10, bottom=24),
                content=ft.Column(spacing=14, controls=[
                    lbl_aviso_pedido,
                    ft.Row([
                        lbl_titulo_secao,
                        ft.TextButton("Ver todos", on_click=lambda e: carregar_vitrine(False))
                    ], alignment="spaceBetween", vertical_alignment="center"),
                    lista_vitrine
                ])
            )

            corpo_rolavel = ft.Column(
                scroll="auto",
                expand=True,
                spacing=0,
                controls=[
                    bloco_topo_branco,
                    banner_azul,
                    secao_vitrine
                ]
            )

            nav_bar = ft.Container(
                bgcolor="#FFFFFF",
                padding=ft.Padding(top=10, bottom=12, left=16, right=16),
                border=ft.Border(top=ft.BorderSide(1, "#E2E8F0")),
                content=ft.Row([
                    ft.Container(on_click=lambda e: carregar_vitrine(False), expand=True, content=ft.Column([ft.Icon(ft.Icons.HOME, color="#0066FF", size=24), ft.Text("Início", size=11, color="#0066FF", weight="bold")], spacing=3, horizontal_alignment="center")),
                    ft.Container(on_click=lambda e: carregar_vitrine(True), expand=True, content=ft.Column([ft.Icon(ft.Icons.SEARCH, color="#64748B", size=24), ft.Text("Plantão 24h", size=11, color="#64748B")], spacing=3, horizontal_alignment="center")),
                    ft.Container(expand=True, content=ft.Column([ft.Icon(ft.Icons.RECEIPT_LONG, color="#64748B", size=24), ft.Text("Pedidos", size=11, color="#64748B")], spacing=3, horizontal_alignment="center")),
                    ft.Container(on_click=lambda e: mostrar_tela("login"), expand=True, content=ft.Column([ft.Icon(ft.Icons.PERSON, color="#64748B", size=24), ft.Text("Sair", size=11, color="#64748B")], spacing=3, horizontal_alignment="center")),
                ], alignment="spaceAround")
            )

            page.add(criar_moldura_mobile(corpo_rolavel, nav_bar))

        elif nome_tela == "prestador_home":
            pid = usuario_logado['id']
            nome_oficina = usuario_logado['nome']
            lista_pedidos = ft.Column(spacing=14)

            def carregar_pedidos():
                lista_pedidos.controls.clear()
                pedidos = buscar_pedidos_prestador(pid)
                
                if not pedidos:
                    lista_pedidos.controls.append(
                        ft.Container(
                            padding=24, bgcolor="#FFFFFF", border_radius=16, border=ft.Border.all(1, "#E2E8F0"),
                            content=ft.Text("Nenhum chamado pendente no momento.", color="#64748B", text_align="center")
                        )
                    )
                
                for p in pedidos:
                    status = p['status']
                    
                    def aceitar(e, ped_id=p['id']):
                        marcar_pedido_aceito(ped_id, pid)
                        carregar_pedidos()
                        
                    def abrir_whatsapp(e, tel=p['cliente_telefone'], ped_id=p['id']):
                        numero_limpo = str(tel).replace(" ", "").replace("-", "")
                        mensagem = urllib.parse.quote(f"Olá! Sou da oficina, falo sobre o chamado #{ped_id} no App Automotivo.")
                        webbrowser.open(f"https://wa.me/55{numero_limpo}?text={mensagem}")
                        
                    def abrir_maps(e, lat=p['lat_cliente'], lon=p['lon_cliente']):
                        destino = f"{lat},{lon}" if lat and lon else "-19.9166,-43.9344"
                        webbrowser.open(f"https://www.google.com/maps/dir/?api=1&destination={destino}")

                    if status == 'pendente':
                        botoes = ft.Row([criar_botao("Aceitar Chamado (R$ 1,00)", aceitar, "#16A34A", "white", 46, expandir=True)])
                    else:
                        botoes = ft.Column([
                            ft.Row([criar_botao(f"WhatsApp: {p['cliente_telefone']}", abrir_whatsapp, "#25D366", "white", 44, expandir=True)]),
                            ft.Row([criar_botao("Iniciar Rota no Google Maps", abrir_maps, "#0066FF", "white", 44, expandir=True)])
                        ], spacing=8)

                    card = ft.Container(
                        padding=18, bgcolor="#FFFFFF", border_radius=16,
                        border=ft.Border.all(1.5, "#F59E0B" if status == 'pendente' else "#22C55E"),
                        shadow=ft.BoxShadow(blur_radius=8, color="#0A000000", offset=ft.Offset(0, 3)),
                        content=ft.Column([
                            ft.Row([
                                ft.Text(f"Cliente: {p['cliente_nome']}", weight="bold", size=16, color="#0F172A"),
                                ft.Container(
                                    padding=ft.Padding(left=10, right=10, top=4, bottom=4),
                                    border_radius=12,
                                    bgcolor="#FEF3C7" if status == 'pendente' else "#DCFCE7",
                                    content=ft.Text(status.upper(), color="#B45309" if status == 'pendente' else "#15803D", weight="bold", size=11)
                                )
                            ], alignment="spaceBetween"),
                            ft.Divider(color="#F1F5F9"),
                            botoes
                        ], spacing=10)
                    )
                    lista_pedidos.controls.append(card)
                page.update()

            carregar_pedidos()

            corpo_prestador = ft.Column(
                scroll="auto", expand=True, spacing=0,
                controls=[
                    ft.Container(
                        bgcolor="#EA580C", padding=22,
                        content=ft.Row([
                            ft.Column([
                                ft.Text(nome_oficina, color="white", weight="bold", size=20),
                                ft.Text("Central de Chamados e Plantão", color="#FFEDD5", size=13)
                            ], expand=True),
                            ft.IconButton(icon=ft.Icons.LOGOUT, icon_color="white", on_click=lambda e: mostrar_tela("login"))
                        ])
                    ),
                    ft.Container(
                        padding=20,
                        content=ft.Column(spacing=16, controls=[
                            ft.Row([criar_botao("Atualizar Lista de Chamados", lambda e: carregar_pedidos(), "#0F172A", "white", 46, expandir=True)]),
                            lista_pedidos
                        ])
                    )
                ]
            )
            page.add(criar_moldura_mobile(corpo_prestador))

        elif nome_tela == "admin":
            conteudo = ft.Container(
                padding=24, expand=True, bgcolor="#FFFFFF",
                content=ft.Column([
                    ft.Text("Painel Administrativo", size=22, weight="bold", color="#0F172A"),
                    ft.Text("Sessão de administrador ativa.", color="#64748B"),
                    ft.Container(height=20),
                    ft.Row([criar_botao("Encerrar Sessão", lambda e: mostrar_tela("login"), "#DC2626", "white", 48, expandir=True)])
                ])
            )
            page.add(criar_moldura_mobile(conteudo))

        page.update()

    mostrar_tela("login")

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8000))
    
    if hasattr(ft, "run"):
        ft.run(main, view=ft.AppView.WEB_BROWSER, port=porta, assets_dir="assets")
    else:
        ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=porta, assets_dir="assets")