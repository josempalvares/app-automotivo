import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import flet as ft
import urllib.parse
import urllib.request
import webbrowser
import database as db
import psycopg2.extras
import os
import base64
import re
import threading
import time

# =========================================================================
# SISTEMA KEEP-ALIVE: Impede que o servidor gratuito da Render "durma"
# =========================================================================
_keep_alive_iniciado = False

def iniciar_keep_alive():
    global _keep_alive_iniciado
    if _keep_alive_iniciado:
        return
    _keep_alive_iniciado = True

    def ping_loop():
        url_render = os.environ.get("RENDER_EXTERNAL_URL")
        porta = os.environ.get("PORT", "8000")
        url_alvo = url_render if url_render else f"http://127.0.0.1:{porta}"
        while True:
            time.sleep(600)
            try:
                req = urllib.request.Request(url_alvo, headers={"User-Agent": "KeepAlive-Monitor/1.0"})
                urllib.request.urlopen(req, timeout=10)
            except Exception:
                pass

    t = threading.Thread(target=ping_loop, daemon=True)
    t.start()

iniciar_keep_alive()

def carregar_logo_base64():
    caminho_svg = os.path.join("assets", "logo.svg")
    if os.path.exists(caminho_svg):
        try:
            with open(caminho_svg, "r", encoding="utf-8") as f:
                svg_content = f.read()
            svg_content = re.sub(
                r'<path[^>]*fill="#(?:[fF]{6}|[fF][eE][fF][eE][fF][eE]|[fF][dD][fF][dD][fF][dD])"[^>]*/>\s*',
                '',
                svg_content,
                count=1
            )
            b64 = base64.b64encode(svg_content.encode("utf-8")).decode("utf-8")
            return f"data:image/svg+xml;base64,{b64}"
        except Exception:
            pass
    for nome_png in ["logo_transparente.png", "logo_180.png", "favicon.png"]:
        caminho_png = os.path.join("assets", nome_png)
        if os.path.exists(caminho_png):
            try:
                with open(caminho_png, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                return f"data:image/png;base64,{b64}"
            except Exception:
                pass
    return "favicon.png"

# =========================================================================
# BASE NACIONAL DE CONCESSIONÁRIAS (0800 EMERGÊNCIA 24H)
# =========================================================================
CONCESSIONARIAS_BRASIL = [
    {"nome": "Arteris Fernão Dias", "rodovia": "BR-381 (BH / São Paulo)", "uf": "MG/SP", "fone": "0800 283 0381"},
    {"nome": "EPR Via Mineira", "rodovia": "BR-040 (BH / Juiz de Fora)", "uf": "MG", "fone": "0800 003 1040"},
    {"nome": "Via Cristais (BR-040)", "rodovia": "BR-040 (BH / Cristalina-GO)", "uf": "MG/GO", "fone": "0800 040 0040"},
    {"nome": "Nova 381", "rodovia": "BR-381 (BH / Gov. Valadares)", "uf": "MG", "fone": "0800 038 1381"},
    {"nome": "Way-262 / Concebra", "rodovia": "BR-262 e BR-153", "uf": "MG/GO", "fone": "0800 060 6000"},
    {"nome": "Eco135", "rodovia": "BR-135, MG-231 e LMG-754", "uf": "MG", "fone": "0800 013 5135"},
    {"nome": "Eco050", "rodovia": "BR-050 (Triângulo / GO)", "uf": "MG/GO", "fone": "0800 940 0700"},
    {"nome": "EPR Sul de Minas", "rodovia": "MG-290, BR-459 (Sul MG)", "uf": "MG", "fone": "0800 290 0400"},
    {"nome": "EPR Triângulo", "rodovia": "BR-452, BR-365, MG-190", "uf": "MG", "fone": "0800 452 0365"},
    {"nome": "EPR Vias do Café", "rodovia": "BR-146, BR-265, MG-167", "uf": "MG", "fone": "0800 265 0491"},
    {"nome": "Via Nascentes", "rodovia": "MG-050, BR-265, BR-491", "uf": "MG", "fone": "0800 282 0505"},
    {"nome": "EcoRioMinas", "rodovia": "BR-116, BR-465 e BR-493", "uf": "MG/RJ", "fone": "0800 116 0493"},
    {"nome": "CCR RioSP (Via Dutra)", "rodovia": "BR-116 e BR-101 (SP / RJ)", "uf": "SP/RJ", "fone": "0800 017 3536"},
    {"nome": "Concer", "rodovia": "BR-040 (Juiz de Fora / RJ)", "uf": "MG/RJ", "fone": "0800 282 0040"},
    {"nome": "Ecovias (Imigrantes/Anchieta)", "rodovia": "SP-150 e SP-160", "uf": "SP", "fone": "0800 019 7878"},
    {"nome": "CCR AutoBAn", "rodovia": "Anhanguera e Bandeirantes", "uf": "SP", "fone": "0800 055 5550"},
    {"nome": "CCR ViaOeste / SPVias", "rodovia": "Castelo Branco e Raposo", "uf": "SP", "fone": "0800 701 5555"},
    {"nome": "Arteris Régis Bittencourt", "rodovia": "BR-116 (SP / Curitiba)", "uf": "SP/PR", "fone": "0800 709 0116"},
    {"nome": "Ecopistas", "rodovia": "Ayrton Senna/Carvalho Pinto", "uf": "SP", "fone": "0800 777 0070"},
    {"nome": "Rota das Bandeiras", "rodovia": "Corredor Dom Pedro (SP-065)", "uf": "SP", "fone": "0800 770 8070"},
    {"nome": "Arteris Fluminense", "rodovia": "BR-101 (Niterói / ES)", "uf": "RJ", "fone": "0800 282 0101"},
    {"nome": "Arteris Litoral Sul", "rodovia": "BR-116/101 (Curitiba / SC)", "uf": "PR/SC", "fone": "0800 725 1771"},
    {"nome": "Arteris Planalto Sul", "rodovia": "BR-116 (PR / SC / RS)", "uf": "PR/SC", "fone": "0800 717 1000"},
    {"nome": "CCR ViaSul", "rodovia": "BR-101, BR-290 e BR-386", "uf": "RS/SC", "fone": "0800 000 0290"},
    {"nome": "Eco101", "rodovia": "BR-101 (ES / Sul da Bahia)", "uf": "ES/BA", "fone": "0800 770 1101"},
    {"nome": "ViaBahia", "rodovia": "BR-324 e BR-116 (Bahia)", "uf": "BA", "fone": "0800 600 0324"},
    {"nome": "Ecovias do Araguaia", "rodovia": "BR-153, BR-414 e BR-080", "uf": "GO/TO", "fone": "0800 153 0153"},
    {"nome": "CCR MSVia", "rodovia": "BR-163 (Mato Grosso do Sul)", "uf": "MS", "fone": "0800 648 0163"},
    {"nome": "Nova Rota do Oeste", "rodovia": "BR-163 e BR-364 (MT)", "uf": "MT", "fone": "0800 065 0163"},
]


def criar_borda_input(cor_normal="#94A3B8", cor_foco="#0066FF", raio=12):
    """Cria borda compatível tanto com Flet 1.0+ (side=) quanto versões anteriores."""
    try:
        b_normal = ft.OutlineInputBorder(border_radius=raio, side=ft.BorderSide(1, cor_normal))
        b_foco = ft.OutlineInputBorder(border_radius=raio, side=ft.BorderSide(2, cor_foco))
        if hasattr(ft, "ControlState"):
            return {
                ft.ControlState.DEFAULT: b_normal,
                ft.ControlState.FOCUSED: b_foco,
            }
        return b_normal
    except Exception:
        return None


def main(page: ft.Page):
    page.title = "App Automotivo"
    page.theme_mode = "light"
    page.padding = 0
    page.spacing = 0
    page.bgcolor = "#F2F4F8"

    try:
        page.window.width = 400
        page.window.height = 840
    except Exception:
        pass

    logo_src = carregar_logo_base64()

    def abrir_link(url_alvo):
        try:
            page.launch_url(url_alvo)
        except Exception:
            try:
                webbrowser.open(url_alvo)
            except Exception:
                pass

    def discar_emergencia(numero):
        numero_limpo = re.sub(r"[^0-9]", "", str(numero))
        abrir_link(f"tel:{numero_limpo}")

    def criar_moldura_mobile(conteudo_principal, barra_inferior=None):
        coluna_interna = [ft.Container(content=conteudo_principal, expand=True)]
        if barra_inferior:
            coluna_interna.append(barra_inferior)

        largura_tela = page.width if page.width else 0
        usar_largura_fixa = largura_tela > 500

        return ft.Container(
            expand=True,
            bgcolor="#E2E8F0" if usar_largura_fixa else "#F2F4F8",
            alignment=ft.Alignment(0, 0),
            content=ft.Container(
                width=420 if usar_largura_fixa else None,
                expand=not usar_largura_fixa,
                bgcolor="#F2F4F8",
                shadow=ft.BoxShadow(blur_radius=20, color="#1A000000", offset=ft.Offset(0, 0)) if usar_largura_fixa else None,
                content=ft.Column(spacing=0, expand=True, controls=coluna_interna)
            )
        )

    def criar_input(label_texto, icone=None, senha=False):
        borda = criar_borda_input("#94A3B8", "#0066FF", 12)
        kwargs = dict(
            label=label_texto,
            password=senha,
            prefix_icon=icone,
            bgcolor="#FFFFFF",
            filled=True,
            content_padding=ft.Padding(left=14, right=14, top=14, bottom=14),
            text_size=14,
            expand=True
        )
        if borda is not None:
            kwargs["border"] = borda
        return ft.TextField(**kwargs)

    def criar_botao(texto, acao_clique, cor_fundo="#0066FF", cor_texto="white", altura=48, expandir=False):
        return ft.Container(
            content=ft.Row([ft.Text(texto, color=cor_texto, weight="w600", size=15)], alignment="center"),
            bgcolor=cor_fundo,
            height=altura,
            border_radius=12,
            ink=True,
            on_click=acao_clique,
            expand=expandir,
            padding=ft.Padding(left=12, right=12, top=0, bottom=0)
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

        # =====================================================================
        # TELA DE LOGIN (SIMÉTRICA, COMPACTA E COM SOS VISÍVEL SEM ROLAGEM)
        # =====================================================================
        if nome_tela == "login":
            txt_telefone = criar_input("Telefone Cadastrado", icone=ft.Icons.PHONE)
            txt_senha = criar_input("Sua Senha", icone=ft.Icons.LOCK, senha=True)
            lbl_erro = ft.Text("", color="#DC2626", weight="w600", size=13, text_align="center")

            def btn_login_click(e):
                tel_digitado = (txt_telefone.value or "").strip()
                senha_digitada = (txt_senha.value or "").strip()

                if not tel_digitado or not senha_digitada:
                    lbl_erro.value = "Preencha o telefone e a senha."
                    lbl_erro.color = "#DC2626"
                    page.update()
                    return

                lbl_erro.value = "Verificando acesso..."
                lbl_erro.color = "#0066FF"
                page.update()

                try:
                    conn = db.get_connection()
                    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    cursor.execute(
                        "SELECT id, nome, tipo_perfil FROM usuarios WHERE TRIM(telefone) = %s AND TRIM(senha_hash) = %s",
                        (tel_digitado, senha_digitada)
                    )
                    user = cursor.fetchone()

                    # Caso tenha digitado com ou sem zero à esquerda (ex: 031 vs 31)
                    if not user and tel_digitado.startswith("0"):
                        cursor.execute(
                            "SELECT id, nome, tipo_perfil FROM usuarios WHERE TRIM(telefone) = %s AND TRIM(senha_hash) = %s",
                            (tel_digitado.lstrip("0"), senha_digitada)
                        )
                        user = cursor.fetchone()

                    conn.close()
                    
                    if user:
                        user_dict = dict(user)
                        perfil = str(user_dict.get('tipo_perfil', 'cliente')).strip().lower()
                        if perfil == 'admin':
                            mostrar_tela("admin")
                        elif perfil == 'prestador':
                            mostrar_tela("prestador_home", user_dict)
                        else:
                            mostrar_tela("cliente_home", user_dict)
                    else:
                        lbl_erro.value = "Telefone ou senha incorretos."
                        lbl_erro.color = "#DC2626"
                        page.update()
                except Exception as ex:
                    lbl_erro.value = f"Falha na conexão: {str(ex)[:60]}"
                    lbl_erro.color = "#DC2626"
                    page.update()

            conteudo = ft.Container(
                bgcolor="#FFFFFF",
                expand=True,
                padding=ft.Padding(left=22, right=22, top=28, bottom=16),
                content=ft.Column(
                    scroll="auto",
                    horizontal_alignment="center",
                    spacing=0,
                    controls=[
                        ft.Container(height=6),
                        ft.Container(
                            alignment=ft.Alignment(0, 0),
                            content=ft.Image(src=logo_src, width=92, height=92, fit="contain")
                        ),
                        ft.Container(height=8),
                        ft.Text("Boas-vindas", size=24, weight="bold", color="#0F172A", text_align="center"),
                        ft.Text("Socorro automotivo rápido na palma da mão", size=13, color="#64748B", text_align="center"),
                        ft.Container(height=18),
                        ft.Row([txt_telefone]),
                        ft.Container(height=10),
                        ft.Row([txt_senha]),
                        ft.Container(height=4),
                        lbl_erro,
                        ft.Container(height=6),
                        ft.Row([criar_botao("Entrar na Conta", btn_login_click, "#0066FF", "white", 50, expandir=True)]),
                        ft.Container(height=4),
                        ft.Row([
                            ft.TextButton("Esqueci a senha", on_click=lambda e: mostrar_tela("recuperar_senha")),
                            ft.TextButton("Criar nova conta", on_click=lambda e: mostrar_tela("cadastro_escolha"))
                        ], alignment="spaceBetween"),
                        ft.Container(height=8),
                        # Botão SOS com a exata mesma largura e altura (52px) dos campos e botão de entrar
                        ft.Row([
                            ft.Container(
                                height=54,
                                bgcolor="#FEF2F2",
                                border=ft.Border.all(1.5, "#EF4444"),
                                border_radius=12,
                                padding=ft.Padding(left=12, right=12, top=6, bottom=6),
                                ink=True,
                                expand=True,
                                on_click=lambda e: mostrar_tela("emergencia", None),
                                content=ft.Row([
                                    ft.Container(
                                        width=34, height=34, border_radius=17, bgcolor="#DC2626",
                                        alignment=ft.Alignment(0, 0),
                                        content=ft.Icon(ft.Icons.PHONE_IN_TALK, color="white", size=18)
                                    ),
                                    ft.Column([
                                        ft.Text("SOS EMERGÊNCIA NA ESTRADA", weight="bold", size=12.5, color="#B91C1C"),
                                        ft.Text("190, 191, 192, 193, GPS e Concessionárias", size=10.5, color="#7F1D1D")
                                    ], spacing=0, alignment="center", expand=True),
                                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color="#DC2626", size=20)
                                ], spacing=10, vertical_alignment="center")
                            )
                        ])
                    ]
                )
            )
            page.add(criar_moldura_mobile(conteudo))

        elif nome_tela == "cadastro_escolha":
            conteudo = ft.Container(
                bgcolor="#FFFFFF", expand=True, padding=22,
                content=ft.Column([
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color="#0F172A", on_click=lambda e: mostrar_tela("login")),
                        ft.Text("Criar Nova Conta", size=20, weight="bold", color="#0F172A")
                    ]),
                    ft.Container(height=16),
                    ft.Text("Como você deseja usar a plataforma?", size=15, color="#475569"),
                    ft.Container(height=16),
                    ft.Container(
                        padding=18, border_radius=16, bgcolor="#F8FAFC", border=ft.Border.all(1, "#E2E8F0"),
                        ink=True, on_click=lambda e: mostrar_tela("cadastro_cliente"),
                        content=ft.Row([
                            ft.Container(padding=12, bgcolor="#DBEAFE", border_radius=12, content=ft.Icon(ft.Icons.DIRECTIONS_CAR, color="#0066FF", size=26)),
                            ft.Column([
                                ft.Text("Sou Motorista / Cliente", weight="bold", size=15, color="#0F172A"),
                                ft.Text("Quero solicitar reboque ou socorro", size=12, color="#64748B")
                            ], spacing=2, expand=True),
                            ft.Icon(ft.Icons.CHEVRON_RIGHT, color="#94A3B8")
                        ], spacing=12)
                    ),
                    ft.Container(height=12),
                    ft.Container(
                        padding=18, border_radius=16, bgcolor="#F8FAFC", border=ft.Border.all(1, "#E2E8F0"),
                        ink=True, on_click=lambda e: mostrar_tela("cadastro_prestador"),
                        content=ft.Row([
                            ft.Container(padding=12, bgcolor="#FFEDD5", border_radius=12, content=ft.Icon(ft.Icons.BUILD, color="#EA580C", size=26)),
                            ft.Column([
                                ft.Text("Sou Oficina / Prestador", weight="bold", size=15, color="#0F172A"),
                                ft.Text("Quero atender clientes na região", size=12, color="#64748B")
                            ], spacing=2, expand=True),
                            ft.Icon(ft.Icons.CHEVRON_RIGHT, color="#94A3B8")
                        ], spacing=12)
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
                elif db.telefone_existe(txt_telefone.value.strip()):
                    lbl_aviso.value = "Este telefone já está cadastrado!"
                    lbl_aviso.color = "#DC2626"
                else:
                    db.cadastrar_usuario_cliente(txt_nome.value.strip(), txt_telefone.value.strip(), txt_senha.value.strip())
                    lbl_aviso.value = "Conta criada com sucesso! Volte ao login."
                    lbl_aviso.color = "#16A34A"
                    txt_nome.value = txt_telefone.value = txt_senha.value = ""
                page.update()

            conteudo = ft.Container(
                bgcolor="#FFFFFF", expand=True, padding=22,
                content=ft.Column([
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color="#0F172A", on_click=lambda e: mostrar_tela("cadastro_escolha")),
                        ft.Text("Cadastro de Cliente", size=20, weight="bold", color="#0F172A")
                    ]),
                    ft.Container(height=15),
                    ft.Row([txt_nome]), ft.Container(height=10),
                    ft.Row([txt_telefone]), ft.Container(height=10),
                    ft.Row([txt_senha]), ft.Container(height=10),
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
                elif db.telefone_existe(txt_telefone.value.strip()):
                    lbl_aviso.value = "Este telefone já está cadastrado!"
                    lbl_aviso.color = "#DC2626"
                else:
                    db.cadastrar_usuario_prestador(txt_nome.value.strip(), txt_telefone.value.strip(), txt_senha.value.strip(), txt_oficina.value.strip(), chk_24h.value)
                    lbl_aviso.value = "Oficina cadastrada com sucesso! Faça login."
                    lbl_aviso.color = "#16A34A"
                    txt_nome.value = txt_oficina.value = txt_telefone.value = txt_senha.value = ""
                page.update()

            conteudo = ft.Container(
                bgcolor="#FFFFFF", expand=True, padding=22,
                content=ft.Column(scroll="auto", controls=[
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color="#0F172A", on_click=lambda e: mostrar_tela("cadastro_escolha")),
                        ft.Text("Cadastro de Parceiro", size=20, weight="bold", color="#0F172A")
                    ]),
                    ft.Container(height=15),
                    ft.Row([txt_nome]), ft.Container(height=10),
                    ft.Row([txt_oficina]), ft.Container(height=10),
                    ft.Row([txt_telefone]), ft.Container(height=10),
                    ft.Row([txt_senha]), ft.Container(height=10),
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
                if not db.telefone_existe((txt_telefone.value or "").strip()):
                    lbl_aviso.value = "Telefone não encontrado!"
                    lbl_aviso.color = "#DC2626"
                else:
                    db.redefinir_senha(txt_telefone.value.strip(), txt_nova_senha.value.strip())
                    lbl_aviso.value = "Senha atualizada com sucesso!"
                    lbl_aviso.color = "#16A34A"
                page.update()

            conteudo = ft.Container(
                bgcolor="#FFFFFF", expand=True, padding=22,
                content=ft.Column([
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color="#0F172A", on_click=lambda e: mostrar_tela("login")),
                        ft.Text("Recuperar Senha", size=20, weight="bold", color="#0F172A")
                    ]),
                    ft.Container(height=15),
                    ft.Row([txt_telefone]), ft.Container(height=10),
                    ft.Row([txt_nova_senha]), ft.Container(height=10),
                    lbl_aviso,
                    ft.Row([criar_botao("Redefinir Senha", salvar_nova_senha, "#0066FF", "white", 50, expandir=True)])
                ])
            )
            page.add(criar_moldura_mobile(conteudo))

        # =====================================================================
        # CENTRAL SOS DE EMERGÊNCIA + LOCALIZAÇÃO E ORIENTAÇÃO SEM SINAL
        # =====================================================================
        elif nome_tela == "emergencia":
            tela_retorno = "cliente_home" if usuario_logado else "login"
            
            lbl_gps = ft.Text("Toque aqui para identificar sua rodovia/posição no mapa ou filtrar abaixo.", size=11.5, color="#15803D")

            def buscar_gps(e):
                lbl_gps.value = "Abrindo localização exata no Google Maps para leitura da via/KM..."
                page.update()
                abrir_link("https://www.google.com/maps/search/?api=1&query=minha+localizacao+atual")

            def criar_botao_urgencia_topo(sigla, numero, subtitulo, cor_fundo, icone):
                return ft.Container(
                    expand=True, bgcolor=cor_fundo, border_radius=14,
                    padding=ft.Padding(left=10, right=10, top=10, bottom=10),
                    ink=True, shadow=ft.BoxShadow(blur_radius=6, color="#22000000", offset=ft.Offset(0, 3)),
                    on_click=lambda e, num=numero: discar_emergencia(num),
                    content=ft.Row([
                        ft.Column([
                            ft.Row([
                                ft.Icon(icone, color="white", size=16),
                                ft.Text(sigla, color="white", weight="bold", size=12.5),
                            ], spacing=4),
                            ft.Text(numero, color="white", weight="bold", size=21),
                            ft.Text(subtitulo, color="#F1F5F9", size=10, no_wrap=True)
                        ], spacing=1, expand=True),
                        ft.Container(
                            width=36, height=36, border_radius=18, bgcolor="#FFFFFF",
                            alignment=ft.Alignment(0, 0),
                            content=ft.Icon(ft.Icons.PHONE_IN_TALK, color=cor_fundo, size=19)
                        )
                    ], vertical_alignment="center")
                )

            lista_concessionarias_ui = ft.Column(spacing=8)

            def criar_item_concessionaria(item):
                num = item["fone"]
                return ft.Container(
                    padding=ft.Padding(left=12, right=12, top=10, bottom=10),
                    bgcolor="#FFFFFF", border_radius=12, border=ft.Border.all(1, "#CBD5E1"),
                    ink=True, on_click=lambda e, n=num: discar_emergencia(n),
                    content=ft.Row([
                        ft.Container(
                            padding=ft.Padding(left=8, right=8, top=6, bottom=6),
                            bgcolor="#EFF6FF", border_radius=8,
                            content=ft.Text(item["uf"], weight="bold", size=11, color="#0066FF")
                        ),
                        ft.Column([
                            ft.Text(item["nome"], weight="bold", size=14, color="#0F172A"),
                            ft.Text(item["rodovia"], size=11, color="#475569"),
                            ft.Text(f"📞 {num}", weight="bold", size=13, color="#16A34A")
                        ], spacing=1, expand=True),
                        ft.Container(
                            width=40, height=40, border_radius=20, bgcolor="#16A34A",
                            alignment=ft.Alignment(0, 0),
                            shadow=ft.BoxShadow(blur_radius=4, color="#3316A34A", offset=ft.Offset(0, 2)),
                            content=ft.Icon(ft.Icons.CALL, color="white", size=20)
                        )
                    ], spacing=10, vertical_alignment="center")
                )

            def filtrar_concessionarias(termo=""):
                lista_concessionarias_ui.controls.clear()
                t = termo.strip().lower()
                filtradas = [
                    c for c in CONCESSIONARIAS_BRASIL
                    if not t or t in c["nome"].lower() or t in c["rodovia"].lower() or t in c["uf"].lower() or t in c["fone"].lower()
                ]
                for c in filtradas:
                    lista_concessionarias_ui.controls.append(criar_item_concessionaria(c))
                page.update()

            filtrar_concessionarias("")

            borda_sos = criar_borda_input("#94A3B8", "#DC2626", 10)
            kwargs_sos = dict(
                hint_text="Filtrar rodovia, cidade ou UF (ex: 381, 040, MG, SP)...",
                prefix_icon=ft.Icons.SEARCH, bgcolor="#FFFFFF", filled=True,
                content_padding=ft.Padding(left=12, right=12, top=10, bottom=10),
                text_size=13, expand=True,
                on_change=lambda e: filtrar_concessionarias(e.control.value)
            )
            if borda_sos is not None:
                kwargs_sos["border"] = borda_sos
            txt_filtro_sos = ft.TextField(**kwargs_sos)

            conteudo_sos = ft.Container(
                expand=True,
                bgcolor="#F8FAFC",
                content=ft.Column(scroll="auto", spacing=0, controls=[
                    ft.Container(
                        bgcolor="#DC2626", padding=ft.Padding(left=12, right=16, top=14, bottom=14),
                        content=ft.Row([
                            ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color="white", on_click=lambda e: mostrar_tela(tela_retorno, usuario_logado)),
                            ft.Column([
                                ft.Text("SOS EMERGÊNCIA 24H", size=18, weight="bold", color="white"),
                                ft.Text("Toque em qualquer número para ligar na hora", size=11, color="#FEE2E2")
                            ], spacing=1, expand=True),
                            ft.Icon(ft.Icons.EMERGENCY, color="white", size=28)
                        ])
                    ),
                    ft.Container(
                        padding=ft.Padding(left=14, right=14, top=12, bottom=24),
                        content=ft.Column(spacing=10, controls=[
                            # Alerta de Sobrevivência Sem Sinal / Sem Chip
                            ft.Container(
                                padding=12, bgcolor="#FFFBEB", border_radius=12, border=ft.Border.all(1.5, "#F59E0B"),
                                content=ft.Row([
                                    ft.Icon(ft.Icons.CELL_TOWER, color="#D97706", size=26),
                                    ft.Column([
                                        ft.Text("SINAL FRACO OU SEM OPERADORA?", weight="bold", size=12.5, color="#92400E"),
                                        ft.Text("Ligue 190 (Polícia), 191 (PRF) ou 193 (Bombeiros). Chamadas de emergência usam antenas de qualquer operadora, mesmo sem internet ou sem chip.", size=11, color="#B45309")
                                    ], spacing=2, expand=True)
                                ])
                            ),
                            # Botão de Localização p/ quem não sabe onde está
                            ft.Container(
                                padding=12, bgcolor="#F0FDF4", border_radius=12, border=ft.Border.all(1.5, "#22C55E"),
                                ink=True, on_click=buscar_gps,
                                content=ft.Row([
                                    ft.Icon(ft.Icons.LOCATION_ON, color="#16A34A", size=26),
                                    ft.Column([
                                        ft.Text("📍 Não sabe em qual estrada está?", weight="bold", size=13.5, color="#15803D"),
                                        lbl_gps
                                    ], spacing=2, expand=True),
                                    ft.Icon(ft.Icons.MY_LOCATION, color="#16A34A")
                                ])
                            ),
                            ft.Text("DISCAR URGÊNCIA (1 TOQUE):", weight="bold", size=12, color="#475569"),
                            ft.Row([
                                criar_botao_urgencia_topo("PRF FEDERAL", "191", "Rodovias Federais", "#047857", ft.Icons.MINOR_CRASH),
                                criar_botao_urgencia_topo("SAMU MÉDICO", "192", "Ambulância 24h", "#DC2626", ft.Icons.MEDICAL_SERVICES),
                            ], spacing=8),
                            ft.Row([
                                criar_botao_urgencia_topo("BOMBEIROS", "193", "Resgate / Acidente", "#EA580C", ft.Icons.LOCAL_FIRE_DEPARTMENT),
                                criar_botao_urgencia_topo("POLÍCIA MILITAR", "190", "Qualquer Operadora", "#1E3A8A", ft.Icons.LOCAL_POLICE),
                            ], spacing=8),
                            ft.Row([
                                criar_botao_urgencia_topo("POL. RODOVIÁRIA", "198", "Rodovias Estaduais", "#334155", ft.Icons.DIRECTIONS_CAR),
                                criar_botao_urgencia_topo("DEFESA CIVIL", "199", "Alagamento/Queda", "#B45309", ft.Icons.WARNING),
                            ], spacing=8),
                            ft.Row([
                                criar_botao_urgencia_topo("POLÍCIA CIVIL", "197", "Apoio / Ocorrência", "#1E293B", ft.Icons.SECURITY),
                                criar_botao_urgencia_topo("ANTT RODOVIAS", "166", "Concessões Federais", "#0284C7", ft.Icons.SUPPORT_AGENT),
                            ], spacing=8),
                            ft.Divider(height=16, color="#CBD5E1"),
                            ft.Row([
                                ft.Icon(ft.Icons.ADD_ROAD, color="#0066FF", size=20),
                                ft.Text("Socorro 0800 das Concessionárias", weight="bold", size=16, color="#0F172A")
                            ], spacing=6),
                            ft.Row([txt_filtro_sos]),
                            lista_concessionarias_ui
                        ])
                    )
                ])
            )
            page.add(criar_moldura_mobile(conteudo_sos))

        # =====================================================================
        # HOME DO CLIENTE (100% CENTRALIZADA E ALINHADA NO CELULAR)
        # =====================================================================
        elif nome_tela == "cliente_home":
            lat_cliente, lon_cliente = -19.9386, -43.9341
            lista_vitrine = ft.Column(spacing=16)
            lbl_titulo_secao = ft.Text("Oficinas e Socorro", weight="bold", size=18, color="#0F172A")
            lbl_aviso_pedido = ft.Container(visible=False)

            filtro_atual = [False]
            imagens_demo = ["mecanico_destaque.jpg", "reboque_socorro.jpg", "troca_pneu.jpg"]

            borda_busca = criar_borda_input("#CBD5E1", "#0066FF", 12)
            kwargs_busca = dict(
                hint_text="O que você precisa hoje?",
                prefix_icon=ft.Icons.SEARCH, bgcolor="#F1F5F9", filled=True,
                content_padding=ft.Padding(left=12, right=12, top=12, bottom=12),
                text_size=14, expand=True,
                on_change=lambda e: carregar_vitrine(filtro_atual[0], e.control.value)
            )
            if borda_busca is not None:
                kwargs_busca["border"] = borda_busca
            txt_busca = ft.TextField(**kwargs_busca)

            # Cada botão usa expand=True para dividir a largura da tela em 5 partes iguais sem nunca cortar na direita!
            def criar_card_categoria(icone, cor_icone, titulo, sub, acao, destaque_sos=False):
                return ft.Container(
                    expand=True,
                    on_click=acao,
                    ink=True,
                    content=ft.Column(
                        horizontal_alignment="center",
                        spacing=4,
                        controls=[
                            ft.Container(
                                width=52, height=52,
                                bgcolor="#DC2626" if destaque_sos else "#FFFFFF",
                                border_radius=14,
                                border=ft.Border.all(1.5, "#DC2626" if destaque_sos else "#E2E8F0"),
                                alignment=ft.Alignment(0, 0),
                                shadow=ft.BoxShadow(blur_radius=6, color="#33DC2626" if destaque_sos else "#08000000", offset=ft.Offset(0, 2)),
                                content=ft.Icon(icone, color="white" if destaque_sos else cor_icone, size=24)
                            ),
                            ft.Text(titulo, size=10.5, weight="bold" if destaque_sos else "w600", color="#DC2626" if destaque_sos else "#1E293B", text_align="center", no_wrap=True),
                            ft.Text(sub, size=9.5, color="#DC2626" if destaque_sos else "#64748B", text_align="center", no_wrap=True)
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
                        ft.Container(padding=24, bgcolor="#FFFFFF", border_radius=16, content=ft.Text("Nenhum prestador encontrado para este filtro.", color="#64748B", text_align="center"))
                    )

                for i, p in enumerate(prestadores):
                    aberto = p['aberto_agora']
                    img_src = imagens_demo[i % len(imagens_demo)] 
                    
                    def solicitar_pedido(e, pid=p['id'], nome_of=p['nome_oficina']):
                        criar_pedido(usuario_logado['id'], pid)
                        lbl_aviso_pedido.visible = True
                        lbl_aviso_pedido.content = ft.Container(
                            padding=12, bgcolor="#DCFCE7", border_radius=12, border=ft.Border.all(1, "#86EFAC"),
                            content=ft.Row([
                                ft.Icon(ft.Icons.CHECK_CIRCLE, color="#16A34A", size=20),
                                ft.Text(f"Pedido enviado para {nome_of}! Aguarde o aceite.", color="#15803D", weight="w600", size=12, expand=True)
                            ])
                        )
                        page.update()

                    card_oficina = ft.Container(
                        bgcolor="#FFFFFF", border_radius=16, border=ft.Border.all(1, "#E2E8F0"), clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                        shadow=ft.BoxShadow(blur_radius=10, color="#0A000000", offset=ft.Offset(0, 4)),
                        content=ft.Column(spacing=0, controls=[
                            ft.Stack([
                                ft.Row([ft.Image(src=img_src, height=150, expand=True, fit="cover")]),
                                ft.Container(
                                    content=ft.Row([
                                        ft.Container(width=7, height=7, border_radius=4, bgcolor="#FFFFFF"),
                                        ft.Text("ABERTO AGORA" if aberto else "FECHADO", color="white", size=10, weight="bold")
                                    ], spacing=5, tight=True),
                                    bgcolor="#16A34A" if aberto else "#DC2626", padding=ft.Padding(top=5, bottom=5, left=10, right=10), border_radius=20, margin=12
                                )
                            ]),
                            ft.Container(
                                padding=14,
                                content=ft.Column(spacing=8, controls=[
                                    ft.Row([
                                        ft.Text(p['nome_oficina'], weight="bold", size=16, color="#0F172A", expand=True),
                                        ft.Container(
                                            bgcolor="#FEF3C7", padding=ft.Padding(left=8, right=8, top=4, bottom=4), border_radius=8,
                                            content=ft.Row([ft.Icon(ft.Icons.STAR, size=14, color="#D97706"), ft.Text(f"{p['nota_media']}", weight="bold", size=12, color="#92400E")], spacing=3)
                                        )
                                    ], alignment="spaceBetween"),
                                    ft.Row([
                                        ft.Icon(ft.Icons.LOCATION_ON, size=15, color="#64748B"), ft.Text(f"{p['distancia_km']} km de você", color="#64748B", size=12),
                                        ft.Text("•", color="#CBD5E1"), ft.Text("Atendimento Rápido", color="#0066FF", size=12, weight="w500")
                                    ], spacing=4),
                                    ft.Container(height=2),
                                    ft.Row([criar_botao("Solicitar Socorro Imediato", solicitar_pedido, "#0066FF" if aberto else "#94A3B8", "white", 44, expandir=True)])
                                ])
                            )
                        ])
                    )
                    lista_vitrine.controls.append(card_oficina)
                page.update()

            carregar_vitrine(False)
            primeiro_nome = usuario_logado['nome'].split()[0]

            bloco_topo_branco = ft.Container(
                bgcolor="#FFFFFF", padding=ft.Padding(left=16, right=16, top=16, bottom=18),
                content=ft.Column(spacing=14, controls=[
                    ft.Row([
                        ft.Row([
                            ft.Image(src=logo_src, width=42, height=42, fit="contain"),
                            ft.Column([
                                ft.Text("Boas-vindas,", size=12, color="#64748B"),
                                ft.Text(f"{primeiro_nome}!", size=20, weight="bold", color="#0F172A")
                            ], spacing=0)
                        ], spacing=10),
                        ft.IconButton(icon=ft.Icons.LOGOUT, icon_color="#64748B", tooltip="Sair", on_click=lambda e: mostrar_tela("login"))
                    ], alignment="spaceBetween"),
                    ft.Row([txt_busca]),
                    ft.Row(
                        spacing=4,
                        alignment="spaceBetween",
                        vertical_alignment="start",
                        controls=[
                            criar_card_categoria(ft.Icons.EMERGENCY, "#DC2626", "Plantão", "24 Horas", lambda e: carregar_vitrine(True)),
                            criar_card_categoria(ft.Icons.CAR_REPAIR, "#0066FF", "Mecânica", "Geral", lambda e: carregar_vitrine(False)),
                            criar_card_categoria(ft.Icons.LOCAL_SHIPPING, "#D97706", "Reboque", "Guincho", lambda e: carregar_vitrine(True)),
                            criar_card_categoria(ft.Icons.BUILD_CIRCLE, "#16A34A", "Pneus e", "Bateria", lambda e: carregar_vitrine(False)),
                            criar_card_categoria(ft.Icons.PHONE_IN_TALK, "#DC2626", "SOS", "Emergência", lambda e: mostrar_tela("emergencia", usuario_logado), destaque_sos=True),
                        ]
                    )
                ])
            )

            banner_azul = ft.Container(
                margin=ft.Padding(left=16, right=16, top=14, bottom=8), padding=18, border_radius=16,
                gradient=ft.LinearGradient(begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1), colors=["#0052CC", "#0066FF", "#2684FF"]),
                shadow=ft.BoxShadow(blur_radius=12, color="#330066FF", offset=ft.Offset(0, 4)), ink=True, on_click=lambda e: carregar_vitrine(True),
                content=ft.Row([
                    ft.Column([
                        ft.Text("Emergência na via?", color="white", weight="bold", size=17),
                        ft.Text("Acione o plantão 24h mais próximo\ne acompanhe o atendimento.", color="#E0F2FE", size=12),
                    ], spacing=4, expand=True),
                    ft.Container(
                        width=42, height=42, border_radius=21, bgcolor="#0043A6", alignment=ft.Alignment(0, 0),
                        content=ft.Icon(ft.Icons.ARROW_FORWARD, color="white", size=20)
                    )
                ], spacing=10, vertical_alignment="center")
            )

            secao_vitrine = ft.Container(
                padding=ft.Padding(left=16, right=16, top=8, bottom=24),
                content=ft.Column(spacing=12, controls=[
                    lbl_aviso_pedido,
                    ft.Row([lbl_titulo_secao, ft.TextButton("Ver todos", on_click=lambda e: carregar_vitrine(False))], alignment="spaceBetween", vertical_alignment="center"),
                    lista_vitrine
                ])
            )

            corpo_rolavel = ft.Column(scroll="auto", expand=True, spacing=0, controls=[bloco_topo_branco, banner_azul, secao_vitrine])

            nav_bar = ft.Container(
                bgcolor="#FFFFFF", padding=ft.Padding(top=8, bottom=10, left=8, right=8), border=ft.Border(top=ft.BorderSide(1, "#E2E8F0")),
                content=ft.Row([
                    ft.Container(on_click=lambda e: carregar_vitrine(False), expand=True, content=ft.Column([ft.Icon(ft.Icons.HOME, color="#0066FF", size=22), ft.Text("Início", size=11, color="#0066FF", weight="bold")], spacing=2, horizontal_alignment="center")),
                    ft.Container(on_click=lambda e: carregar_vitrine(True), expand=True, content=ft.Column([ft.Icon(ft.Icons.SEARCH, color="#64748B", size=22), ft.Text("Plantão 24h", size=11, color="#64748B")], spacing=2, horizontal_alignment="center")),
                    ft.Container(on_click=lambda e: mostrar_tela("emergencia", usuario_logado), expand=True, content=ft.Column([ft.Icon(ft.Icons.PHONE_IN_TALK, color="#DC2626", size=22), ft.Text("SOS 190/0800", size=11, color="#DC2626", weight="bold")], spacing=2, horizontal_alignment="center")),
                    ft.Container(on_click=lambda e: mostrar_tela("login"), expand=True, content=ft.Column([ft.Icon(ft.Icons.PERSON, color="#64748B", size=22), ft.Text("Sair", size=11, color="#64748B")], spacing=2, horizontal_alignment="center")),
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
                    lista_pedidos.controls.append(ft.Container(padding=24, bgcolor="#FFFFFF", border_radius=16, border=ft.Border.all(1, "#E2E8F0"), content=ft.Text("Nenhum chamado pendente no momento.", color="#64748B", text_align="center")))
                
                for p in pedidos:
                    status = p['status']
                    
                    def aceitar(e, ped_id=p['id']):
                        marcar_pedido_aceito(ped_id, pid)
                        carregar_pedidos()
                        
                    def abrir_whatsapp(e, tel=p['cliente_telefone'], ped_id=p['id']):
                        numero_limpo = str(tel).replace(" ", "").replace("-", "")
                        mensagem = urllib.parse.quote(f"Olá! Sou da oficina, falo sobre o chamado #{ped_id} no App Automotivo.")
                        abrir_link(f"https://wa.me/55{numero_limpo}?text={mensagem}")
                        
                    def abrir_maps(e, lat=p['lat_cliente'], lon=p['lon_cliente']):
                        destino = f"{lat},{lon}" if lat and lon else "-19.9166,-43.9344"
                        abrir_link(f"https://www.google.com/maps/dir/?api=1&destination={destino}")

                    if status == 'pendente':
                        botoes = ft.Row([criar_botao("Aceitar Chamado (R$ 1,00)", aceitar, "#16A34A", "white", 46, expandir=True)])
                    else:
                        botoes = ft.Column([
                            ft.Row([criar_botao(f"WhatsApp: {p['cliente_telefone']}", abrir_whatsapp, "#25D366", "white", 44, expandir=True)]),
                            ft.Row([criar_botao("Iniciar Rota no Google Maps", abrir_maps, "#0066FF", "white", 44, expandir=True)])
                        ], spacing=8)

                    card = ft.Container(
                        padding=16, bgcolor="#FFFFFF", border_radius=16, border=ft.Border.all(1.5, "#F59E0B" if status == 'pendente' else "#22C55E"), shadow=ft.BoxShadow(blur_radius=8, color="#0A000000", offset=ft.Offset(0, 3)),
                        content=ft.Column([
                            ft.Row([
                                ft.Text(f"Cliente: {p['cliente_nome']}", weight="bold", size=15, color="#0F172A", expand=True),
                                ft.Container(padding=ft.Padding(left=10, right=10, top=4, bottom=4), border_radius=12, bgcolor="#FEF3C7" if status == 'pendente' else "#DCFCE7", content=ft.Text(status.upper(), color="#B45309" if status == 'pendente' else "#15803D", weight="bold", size=11))
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
                    ft.Container(bgcolor="#EA580C", padding=18, content=ft.Row([ft.Column([ft.Text(nome_oficina, color="white", weight="bold", size=18), ft.Text("Central de Chamados e Plantão", color="#FFEDD5", size=12)], expand=True), ft.IconButton(icon=ft.Icons.LOGOUT, icon_color="white", on_click=lambda e: mostrar_tela("login"))])),
                    ft.Container(padding=16, content=ft.Column(spacing=14, controls=[ft.Row([criar_botao("Atualizar Lista de Chamados", lambda e: carregar_pedidos(), "#0F172A", "white", 46, expandir=True)]), lista_pedidos]))
                ]
            )
            page.add(criar_moldura_mobile(corpo_prestador))

        elif nome_tela == "admin":
            conteudo = ft.Container(
                padding=22, expand=True, bgcolor="#FFFFFF",
                content=ft.Column([ft.Text("Painel Administrativo", size=22, weight="bold", color="#0F172A"), ft.Text("Sessão de administrador ativa.", color="#64748B"), ft.Container(height=20), ft.Row([criar_botao("Encerrar Sessão", lambda e: mostrar_tela("login"), "#DC2626", "white", 48, expandir=True)])])
            )
            page.add(criar_moldura_mobile(conteudo))

        page.update()

    mostrar_tela("login")

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8000))
    eh_render = "RENDER" in os.environ or "PORT" in os.environ
    
    if hasattr(ft, "run"):
        if eh_render:
            ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=porta, assets_dir="assets")
        else:
            ft.run(main, view=ft.AppView.WEB_BROWSER, port=porta, assets_dir="assets")
    else:
        if eh_render:
            ft.app(target=main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=porta, assets_dir="assets")
        else:
            ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=porta, assets_dir="assets")