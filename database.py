import os
import psycopg2
import psycopg2.extras

# O Render vai tentar buscar a variável "DATABASE_URL" configurada no painel. 
# Se não a encontrar, usa a sua string oficial do Neon.
DB_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_5JmwMXbUoq6R@ep-twilight-hill-b56yar07-pooler.c-7.us-east-2.aws.neon.tech/neondb?sslmode=require")

def get_connection():
    return psycopg2.connect(DB_URL)

def setup_database():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Criando tabelas na nuvem (PostgreSQL usa SERIAL para IDs automáticos)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            telefone VARCHAR(20) UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            nome TEXT NOT NULL,
            tipo_perfil TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prestadores_detalhes (
            usuario_id INTEGER PRIMARY KEY,
            nome_oficina TEXT,
            lat REAL,
            lon REAL,
            atende_24h BOOLEAN,
            aberto_agora BOOLEAN,
            nota_media REAL,
            total_matches_mes INTEGER DEFAULT 0,
            saldo_devedor_matches REAL DEFAULT 0.0,
            status_financeiro TEXT DEFAULT 'ativo',
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos (
            id SERIAL PRIMARY KEY,
            cliente_id INTEGER,
            prestador_id INTEGER,
            modalidade TEXT,
            status TEXT,
            taxa_match_cobrada REAL DEFAULT 0.0,
            lat_cliente REAL,
            lon_cliente REAL,
            data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES usuarios (id),
            FOREIGN KEY (prestador_id) REFERENCES usuarios (id)
        )
    ''')
    
    # Inserir Admin de teste
    cursor.execute("SELECT id FROM usuarios WHERE telefone = '31900000000'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO usuarios (telefone, senha_hash, nome, tipo_perfil) VALUES ('31900000000', 'hash_admin', 'Administrador', 'admin')")
    
    conn.commit()
    conn.close()

def get_prestadores_vitrine(lat_cliente, lon_cliente, filtro_24h=False):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    query = '''
        SELECT u.id, u.nome, p.nome_oficina, p.lat, p.lon, p.atende_24h, p.aberto_agora, p.nota_media 
        FROM usuarios u 
        JOIN prestadores_detalhes p ON u.id = p.usuario_id
        WHERE p.status_financeiro = 'ativo'
    '''
    if filtro_24h:
        query += " AND p.atende_24h = true"
        
    cursor.execute(query)
    prestadores = cursor.fetchall()
    conn.close()
    
    resultados = []
    for p in prestadores:
        d = dict(p)
        d['distancia_km'] = round(abs(d['lat'] - lat_cliente) * 111 + abs(d['lon'] - lon_cliente) * 111, 2)
        resultados.append(d)
        
    return sorted(resultados, key=lambda x: x['distancia_km'])

def telefone_existe(telefone):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE telefone = %s", (telefone,))
    existe = cursor.fetchone() is not None
    conn.close()
    return existe

def cadastrar_usuario_cliente(nome, telefone, senha):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO usuarios (telefone, senha_hash, nome, tipo_perfil) VALUES (%s, %s, %s, 'cliente')", (telefone, senha, nome))
    conn.commit()
    conn.close()

def cadastrar_usuario_prestador(nome, telefone, senha, nome_oficina, atende_24h):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO usuarios (telefone, senha_hash, nome, tipo_perfil) VALUES (%s, %s, %s, 'prestador') RETURNING id", (telefone, senha, nome))
    usuario_id = cursor.fetchone()[0]
    
    cursor.execute("""
        INSERT INTO prestadores_detalhes (usuario_id, nome_oficina, lat, lon, atende_24h, aberto_agora, nota_media, total_matches_mes, saldo_devedor_matches, status_financeiro)
        VALUES (%s, %s, -19.9166, -43.9344, %s, true, 5.0, 0, 0.0, 'ativo')
    """, (usuario_id, nome_oficina, bool(atende_24h)))
    conn.commit()
    conn.close()

def redefinir_senha(telefone, nova_senha):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET senha_hash = %s WHERE telefone = %s", (nova_senha, telefone))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    setup_database()
    print("Sucesso! O Banco de Dados na nuvem (Neon) foi estruturado.")