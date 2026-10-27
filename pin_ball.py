import pygame
import pymunk
import sys
import os
import random
import math

WIDTH, HEIGHT = 600, 800
FPS = 60
LIMITE_LAVA_Y = HEIGHT - 75

ACELERACAO_HORIZONTAL = 1700
VELOCIDADE_HORIZONTAL_MAXIMA = 320

FREIO_HORIZONTAL = 0.85
IMPULSO_VERTICAL = 620
IMPULSO_PROTECAO_FRAMES = 7

TEMPO_RASTRO = 0.32
DISTANCIA_PONTO_RASTRO = 2.0

FREQUENCIA_PARTICULAS_RASTRO = 2.2
VELOCIDADE_MINIMA_PARTICULAS_RASTRO = 75

STAR_X_MIN = 90
STAR_X_MAX = WIDTH - 90
STAR_Y_MIN = 100
STAR_Y_MAX = min(260, LIMITE_LAVA_Y - 90)

SEGMENTOS_OBSTACULOS = [
    ((100, 400), (250, 500)),
    ((500, 400), (350, 500)),
]

BALL_COLOR = (0, 191, 255)
LIGHT_BLUE_COLOR = (130, 230, 255)
LAVA_ORANGE_COLOR = (255, 140, 0)
FLIPPER_COLOR = LAVA_ORANGE_COLOR
CORES_LAVA = [(255, 69, 0), (255, 140, 0), (255, 200, 0)]

FREQUENCIA_FAISCAS_ESTRELA = 0.10

def create_ball(space, x, y, radius=15):
    mass = 1
    moment = pymunk.moment_for_circle(mass, 0, radius)
    body = pymunk.Body(mass, moment)
    body.position = (x, y)

    shape = pymunk.Circle(body, radius)

    shape.elasticity = 0.92
    shape.friction = 0.25

    space.add(body, shape)
    return body, shape

def create_static_obstacle(space, p1, p2, thickness=10, visivel=True):
    body = space.static_body
    shape = pymunk.Segment(body, p1, p2, thickness)

    shape.elasticity = 0.95
    shape.friction = 0.35
    shape.visivel = visivel
    space.add(shape)
    return shape

def draw_pymunk_segments(screen, space):
    for shape in space.shapes:
        if isinstance(shape, pymunk.Segment) and getattr(shape, "visivel", True):
            p1 = (int(shape.a.x), int(shape.a.y))
            p2 = (int(shape.b.x), int(shape.b.y))
            thickness = max(1, int(shape.radius))

            pygame.draw.line(screen, (28, 15, 55), p1, p2, thickness * 2 + 4)
            pygame.draw.line(screen, FLIPPER_COLOR, p1, p2, thickness * 2)

def criar_particula_lava():
    x = random.randint(0, WIDTH)
    y = HEIGHT - random.randint(0, 100)
    raio = random.randint(3, 6)
    velocidade_y = random.uniform(1.5, 3.5)
    cor = random.choice(CORES_LAVA)
    return [x, y, raio, velocidade_y, cor]

def atualizar_particulas_lava(particulas, dt=None):
    for particula in particulas:
        particula[1] -= particula[3]
        particula[2] -= 0.08

    particulas[:] = [particula for particula in particulas if particula[2] > 0]

def _cor_esmaecida(cor, intensidade):
    intensidade = max(0.0, min(1.0, intensidade))
    return tuple(
        max(0, min(255, int(componente * intensidade)))
        for componente in cor
    )

def desenhar_particulas_lava(screen, particulas):
    for particula in particulas:
        pygame.draw.circle(
            screen,
            particula[4],
            (int(particula[0]), int(particula[1])),
            max(1, int(particula[2]))
        )

def criar_particula_estrela(posicao):
    x_centro, y_centro = posicao
    angulo = random.uniform(0, math.pi * 2)
    distancia = random.uniform(10, 24)

    return {
        "x": x_centro + math.cos(angulo) * distancia,
        "y": y_centro + math.sin(angulo) * distancia,
        "vx": math.cos(angulo) * random.uniform(12, 38),
        "vy": math.sin(angulo) * random.uniform(12, 38),
        "idade": 0.0,
        "duracao": random.uniform(0.28, 0.5),
        "tamanho": random.uniform(3.0, 6.0),

        "cor": random.choice([
            (255, 220, 65),
            (255, 255, 255),
        ]),
    }

def atualizar_particulas_estrela(particulas, dt):
    for particula in particulas:
        particula["x"] += particula["vx"] * dt
        particula["y"] += particula["vy"] * dt
        particula["idade"] += dt
        particula["vx"] *= math.exp(-0.8 * dt)
        particula["vy"] *= math.exp(-0.8 * dt)

    particulas[:] = [
        particula for particula in particulas
        if particula["idade"] < particula["duracao"]
    ]

def desenhar_particulas_estrela(surface, particulas):
    for particula in particulas:
        intensidade = max(
            0.0,
            1.0 - particula["idade"] / particula["duracao"]
        )
        if intensidade <= 0:
            continue

        x = int(particula["x"])
        y = int(particula["y"])
        tamanho = max(1, int(particula["tamanho"] * intensidade))
        alpha = int(230 * intensidade)
        cor = particula["cor"]
        cor_alpha = (cor[0], cor[1], cor[2], alpha)

        pygame.draw.line(
            surface,
            (cor[0], cor[1], cor[2], int(alpha * 0.35)),
            (x - tamanho * 2, y),
            (x + tamanho * 2, y),
            max(2, tamanho // 2)
        )
        pygame.draw.line(
            surface,
            (cor[0], cor[1], cor[2], int(alpha * 0.35)),
            (x, y - tamanho * 2),
            (x, y + tamanho * 2),
            max(2, tamanho // 2)
        )

        pygame.draw.line(
            surface, cor_alpha,
            (x - tamanho * 2, y),
            (x + tamanho * 2, y),
            1
        )
        pygame.draw.line(
            surface, cor_alpha,
            (x, y - tamanho * 2),
            (x, y + tamanho * 2),
            1
        )
        pygame.draw.line(
            surface,
            (255, 255, 245, alpha),
            (x - tamanho, y),
            (x + tamanho, y),
            1
        )
        pygame.draw.line(
            surface,
            (255, 255, 245, alpha),
            (x, y - tamanho),
            (x, y + tamanho),
            1
        )

def atualizar_rastro_bolinha(rastro, posicao, dt):
    for ponto in rastro:
        ponto[2] += dt

    rastro[:] = [ponto for ponto in rastro if ponto[2] < TEMPO_RASTRO]

    x_atual, y_atual = posicao

    if not rastro:
        rastro.append([x_atual, y_atual, 0.0])
        return

    x_anterior, y_anterior = rastro[-1][0], rastro[-1][1]
    dx = x_atual - x_anterior
    dy = y_atual - y_anterior
    distancia = math.hypot(dx, dy)
    quantidade_pontos = max(1, math.ceil(distancia / DISTANCIA_PONTO_RASTRO))

    for indice in range(1, quantidade_pontos + 1):
        fracao = indice / quantidade_pontos
        x = x_anterior + dx * fracao
        y = y_anterior + dy * fracao
        idade = dt * (1.0 - fracao)
        rastro.append([x, y, idade])

def atualizar_particulas_rastro(particulas, posicao, velocidade, dt):
    for particula in particulas:
        particula[0] += particula[2] * dt
        particula[1] += particula[3] * dt
        particula[4] += dt

    particulas[:] = [p for p in particulas if p[4] < p[5]]

    vx, vy = velocidade
    rapidez = math.hypot(vx, vy)
    if rapidez < VELOCIDADE_MINIMA_PARTICULAS_RASTRO:
        return

    if random.random() >= FREQUENCIA_PARTICULAS_RASTRO * dt:
        return

    x, y = posicao
    direcao_x = vx / rapidez
    direcao_y = vy / rapidez
    distancia_atras = random.uniform(8, 22)

    px = x - direcao_x * distancia_atras + random.uniform(-3, 3)
    py = y - direcao_y * distancia_atras + random.uniform(-3, 3)

    pvx = -direcao_x * random.uniform(12, 38) + random.uniform(-16, 16)
    pvy = -direcao_y * random.uniform(12, 38) + random.uniform(-16, 16)
    idade_maxima = random.uniform(0.22, 0.34)
    raio = random.uniform(1.4, 2.5)
    cor = random.choice([
        (110, 225, 255),
        (190, 250, 255),
        (255, 255, 255),
    ])

    particulas.append([
        px, py, pvx, pvy, 0.0, idade_maxima, raio, cor
    ])

def desenhar_rastro_bolinha(screen, superficie_rastro, rastro, particulas):
    superficie_rastro.fill((0, 0, 0, 0))

    if rastro:
        x, y, idade = rastro[-1]
        intensidade = max(0.0, 1.0 - idade / TEMPO_RASTRO)

        if intensidade > 0:
            pygame.draw.circle(
                superficie_rastro,
                (0, 150, 255, int(55 * intensidade)),
                (int(x), int(y)),
                max(5, int(18 * intensidade))
            )

    camadas = [
        ((0, 55, 255), 34, 24, 1),
        ((0, 115, 255), 72, 14, 1),
        ((0, 190, 255), 175, 0, 1),
        ((155, 245, 255), 125, 0, 3),
    ]

    for cor, alpha_base, largura_extra, divisor in camadas:
        for indice in range(1, len(rastro)):
            anterior = rastro[indice - 1]
            atual = rastro[indice]

            p1 = (int(anterior[0]), int(anterior[1]))
            p2 = (int(atual[0]), int(atual[1]))

            idade_media = (anterior[2] + atual[2]) / 2.0
            intensidade = max(0.0, 1.0 - idade_media / TEMPO_RASTRO)

            if intensidade <= 0:
                continue

            largura_base = max(4, int(7 + 15 * intensidade))

            if divisor == 3:
                largura = max(2, largura_base // divisor)
            else:
                largura = largura_base + largura_extra

            alpha = int(alpha_base * intensidade)

            pygame.draw.line(
                superficie_rastro,
                (cor[0], cor[1], cor[2], alpha),
                p1,
                p2,
                largura
            )

        for ponto in rastro:
            x, y, idade = ponto
            intensidade = max(0.0, 1.0 - idade / TEMPO_RASTRO)

            if intensidade <= 0:
                continue

            largura_base = max(4, int(7 + 15 * intensidade))

            if divisor == 3:
                largura = max(2, largura_base // divisor)
            else:
                largura = largura_base + largura_extra

            alpha = int(alpha_base * intensidade)
            raio = max(1, largura // 2)

            pygame.draw.circle(
                superficie_rastro,
                (cor[0], cor[1], cor[2], alpha),
                (int(x), int(y)),
                raio
            )

    for particula in particulas:
        x, y, vx, vy, idade, duracao, raio, cor = particula
        intensidade = max(0.0, 1.0 - idade / duracao)

        if intensidade <= 0:
            continue

        px, py = int(x), int(y)
        r = max(1, int(raio * intensidade))
        alpha = int(225 * intensidade)
        cor_alpha = (cor[0], cor[1], cor[2], alpha)

        pygame.draw.line(
            superficie_rastro,
            cor_alpha,
            (px - r * 2, py),
            (px + r * 2, py),
            1
        )

        pygame.draw.line(
            superficie_rastro,
            cor_alpha,
            (px, py - r * 2),
            (px, py + r * 2),
            1
        )

        pygame.draw.circle(
            superficie_rastro,
            cor_alpha,
            (px, py),
            1
        )

    screen.blit(superficie_rastro, (0, 0))

def distancia_ponto_segmento(ponto, inicio, fim):
    px, py = ponto
    x1, y1 = inicio
    x2, y2 = fim
    dx = x2 - x1
    dy = y2 - y1
    comprimento2 = dx * dx + dy * dy

    if comprimento2 == 0:
        return math.hypot(px - x1, py - y1)

    t = ((px - x1) * dx + (py - y1) * dy) / comprimento2
    t = max(0.0, min(1.0, t))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)

def gerar_posicao_estrela():
    margem_obstaculo = 48

    for _ in range(150):
        x = random.randint(STAR_X_MIN, STAR_X_MAX)
        y = random.randint(STAR_Y_MIN, STAR_Y_MAX)

        perto_de_obstaculo = any(
            distancia_ponto_segmento((x, y), inicio, fim) < margem_obstaculo
            for inicio, fim in SEGMENTOS_OBSTACULOS
        )

        if not perto_de_obstaculo:
            return [x, y]

    return [WIDTH // 2, max(STAR_Y_MIN, 180)]

def atualizar_controle_bolinha(ball_body, teclas, dt):
    vx, vy = ball_body.velocity

    esquerda = teclas[pygame.K_LEFT]
    direita = teclas[pygame.K_RIGHT]
    direcao = int(direita) - int(esquerda)

    if direcao != 0:

        vx += direcao * ACELERACAO_HORIZONTAL * dt
    else:

        vx *= math.exp(-FREIO_HORIZONTAL * dt)
        if abs(vx) < 1.5:
            vx = 0

    vx = max(-VELOCIDADE_HORIZONTAL_MAXIMA,
             min(VELOCIDADE_HORIZONTAL_MAXIMA, vx))

    ball_body.activate()
    ball_body.velocity = (vx, vy)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("PIN BALL")
    clock = pygame.time.Clock()

    superficie_rastro = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    superficie_efeitos_estrela = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    caminho_bg = os.path.join("assets", "background.jpeg")
    caminho_tela_inicial = os.path.join("assets", "menu.jpeg")
    caminho_game_over = os.path.join("assets", "game_over.png")
    caminho_start = os.path.join("assets", "botao.png")
    caminho_fonte = os.path.join("assets", "fonte.ttf")
    caminho_coracao = os.path.join("assets", "coracao.png")
    caminho_estrela = os.path.join("assets", "estrela.png")
    caminho_musica = os.path.join("assets", "pin_ball_beat.ogg")

    try:
        pygame.mixer.init()
        pygame.mixer.music.load(caminho_musica)
        pygame.mixer.music.set_volume(0.35)
        pygame.mixer.music.play(-1)
    except (pygame.error, FileNotFoundError) as erro:
        print(f"Nao foi possivel carregar a musica: {erro}")

    try:
        bg_image = pygame.image.load(caminho_bg).convert()
        bg_image = pygame.transform.scale(bg_image, (WIDTH, HEIGHT))
    except (pygame.error, FileNotFoundError) as erro:
        print(f"Erro ao carregar '{caminho_bg}': {erro}")
        pygame.quit()
        sys.exit()

    try:
        tela_inicial_img = pygame.image.load(caminho_tela_inicial).convert()
        tela_inicial_img = pygame.transform.scale(
            tela_inicial_img, (WIDTH, HEIGHT)
        )
    except (pygame.error, FileNotFoundError) as erro:
        print(f"Erro ao carregar '{caminho_tela_inicial}': {erro}")
        pygame.quit()
        sys.exit()

    try:
        game_over_img = pygame.image.load(caminho_game_over).convert()
        game_over_img = pygame.transform.scale(game_over_img, (WIDTH, HEIGHT))
    except (pygame.error, FileNotFoundError):
        print("Aviso: game_over.jpeg nao encontrado; usando o fundo do jogo.")
        game_over_img = bg_image

    try:
        bg_botao_original = pygame.image.load(caminho_start).convert_alpha()
        largura_orig, altura_orig = bg_botao_original.get_size()
        nova_largura_btn = 260
        nova_altura_btn = max(1, int((nova_largura_btn / largura_orig) * altura_orig))
        start_img = pygame.transform.scale(
            bg_botao_original, (nova_largura_btn, nova_altura_btn)
        )

        FATOR_HOVER_BOTAO = 1.06
        start_hover = pygame.transform.smoothscale(
            bg_botao_original,
            (
                int(nova_largura_btn * FATOR_HOVER_BOTAO),
                int(nova_altura_btn * FATOR_HOVER_BOTAO),
            ),
        )

        nova_largura_ui = 150
        nova_altura_ui = max(1, int((nova_largura_ui / largura_orig) * altura_orig))
        ui_panel_img = pygame.transform.scale(
            bg_botao_original, (nova_largura_ui, nova_altura_ui)
        )
    except (pygame.error, FileNotFoundError, ZeroDivisionError) as erro:
        print(f"Erro ao carregar '{caminho_start}': {erro}")
        pygame.quit()
        sys.exit()

    tamanho_icone = (24, 24)
    try:
        coracao_img = pygame.transform.scale(
            pygame.image.load(caminho_coracao).convert_alpha(), tamanho_icone
        )
    except (pygame.error, FileNotFoundError):
        coracao_img = pygame.Surface(tamanho_icone, pygame.SRCALPHA)
        pygame.draw.circle(coracao_img, (255, 0, 0), (12, 12), 12)

    raio_estrela_jogo = 20
    tamanho_estrela_jogo = (raio_estrela_jogo * 2, raio_estrela_jogo * 2)
    try:
        estrela_raw = pygame.image.load(caminho_estrela).convert_alpha()
        estrela_ui_img = pygame.transform.scale(estrela_raw, tamanho_icone)
        estrela_jogo_img = pygame.transform.scale(
            estrela_raw, tamanho_estrela_jogo
        )
    except (pygame.error, FileNotFoundError):
        estrela_ui_img = pygame.Surface(tamanho_icone, pygame.SRCALPHA)
        pygame.draw.polygon(
            estrela_ui_img,
            (255, 215, 0),
            [(12, 0), (15, 9), (24, 9), (17, 15), (20, 24),
             (12, 18), (4, 24), (7, 15), (0, 9), (9, 9)],
        )
        estrela_jogo_img = pygame.transform.scale(
            estrela_ui_img, tamanho_estrela_jogo
        )

    try:
        fonte_titulo = pygame.font.Font(caminho_fonte, 42)
        fonte_ui = pygame.font.Font(caminho_fonte, 24)
        fonte_pequena = pygame.font.Font(caminho_fonte, 18)
    except (pygame.error, FileNotFoundError):
        fonte_titulo = pygame.font.SysFont(None, 64)
        fonte_ui = pygame.font.SysFont(None, 36)
        fonte_pequena = pygame.font.SysFont(None, 24)

    space = pymunk.Space()
    space.gravity = (0, 900)
    space.iterations = 40

    space.damping = 0.999

    create_static_obstacle(space, (100, 400), (250, 500), 8, visivel=True)
    create_static_obstacle(space, (500, 400), (350, 500), 8, visivel=True)

    create_static_obstacle(space, (8, 0), (8, HEIGHT), 8, visivel=False)
    create_static_obstacle(space, (WIDTH - 8, 0), (WIDTH - 8, HEIGHT), 8, visivel=False)
    create_static_obstacle(space, (0, 0), (WIDTH, 0), 8, visivel=False)

    ball_body, ball_shape = create_ball(space, WIDTH // 2, 150)

    vidas = 3
    pontos = 0
    estrela_pos = gerar_posicao_estrela()
    particulas_lava = []
    particulas_estrela = []
    rastro_bolinha = []
    particulas_rastro = []

    estado_jogo = "MENU"
    posicao_y_botao = HEIGHT - 290
    start_rect = start_img.get_rect(center=(WIDTH // 2, posicao_y_botao))

    def desenhar_painel(surface, fundo_img, rect_pos, icone, texto_str):
        surface.blit(fundo_img, rect_pos)
        texto_render = fonte_pequena.render(texto_str, True, (255, 255, 255))
        espaco = 8
        largura_total = icone.get_width() + espaco + texto_render.get_width()
        start_x = rect_pos.centerx - largura_total // 2

        surface.blit(
            icone,
            (start_x, rect_pos.centery - icone.get_height() // 2),
        )
        surface.blit(
            texto_render,
            (start_x + icone.get_width() + espaco,
             rect_pos.centery - texto_render.get_height() // 2),
        )

    fontes_botao_cache = {}

    def renderizar_texto_botao(texto, largura_botao, altura_botao):

        largura_maxima = int(largura_botao * 0.68)
        altura_maxima = int(altura_botao * 0.46)

        for tamanho in range(26, 11, -1):
            if tamanho not in fontes_botao_cache:
                try:
                    fontes_botao_cache[tamanho] = pygame.font.Font(
                        caminho_fonte, tamanho
                    )
                except (pygame.error, FileNotFoundError):
                    fontes_botao_cache[tamanho] = pygame.font.SysFont(
                        None, tamanho
                    )

            fonte = fontes_botao_cache[tamanho]
            texto_render = fonte.render(texto, True, (255, 255, 255))

            if (
                texto_render.get_width() <= largura_maxima
                and texto_render.get_height() <= altura_maxima
            ):
                return texto_render

        fonte_minima = fontes_botao_cache.get(12)
        if fonte_minima is None:
            try:
                fonte_minima = pygame.font.Font(caminho_fonte, 12)
            except (pygame.error, FileNotFoundError):
                fonte_minima = pygame.font.SysFont(None, 12)
            fontes_botao_cache[12] = fonte_minima

        return fonte_minima.render(texto, True, (255, 255, 255))

    def desenhar_botao_principal(surface, texto, pos_mouse):
        sobre_botao = start_rect.inflate(18, 20).collidepoint(pos_mouse)

        if sobre_botao:

            tempo = pygame.time.get_ticks()
            pequeno_salto = int(math.sin(tempo * 0.018) * 2)
            centro = (WIDTH // 2, posicao_y_botao - 7 + pequeno_salto)
            imagem = start_hover
        else:
            centro = (WIDTH // 2, posicao_y_botao)
            imagem = start_img

        rect_visual = imagem.get_rect(center=centro)
        surface.blit(imagem, rect_visual)

        texto_render = renderizar_texto_botao(
            texto, rect_visual.width, rect_visual.height
        )
        surface.blit(
            texto_render,
            texto_render.get_rect(center=rect_visual.center)
        )

    espaco_estava_pressionado = False
    impulso_pendente = False
    impulso_protecao_frames = 0

    def resetar_bolinha():

        nonlocal impulso_pendente, impulso_protecao_frames
        rastro_bolinha.clear()
        particulas_rastro.clear()
        ball_body.activate()
        ball_body.position = (WIDTH // 2, 150)
        ball_body.velocity = (0, 0)
        ball_body.force = (0, 0)
        ball_body.angular_velocity = 0
        ball_body.angle = 0
        impulso_pendente = False
        impulso_protecao_frames = 0
        space.reindex_shapes_for_body(ball_body)

    def iniciar_partida():
        nonlocal vidas, pontos, estrela_pos, estado_jogo
        vidas = 3
        pontos = 0
        estrela_pos = gerar_posicao_estrela()
        particulas_estrela.clear()
        resetar_bolinha()
        estado_jogo = "JOGANDO"

    while True:

        dt = min(clock.tick(FPS) / 1000.0, 1.0 / 30.0)
        if dt <= 0:
            dt = 1.0 / FPS

        pos_mouse = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if estado_jogo in ("MENU", "GAME_OVER"):

                    if start_rect.inflate(18, 20).collidepoint(event.pos):
                        iniciar_partida()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                elif event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    if estado_jogo in ("MENU", "GAME_OVER"):
                        iniciar_partida()

                elif event.key == pygame.K_UP and estado_jogo == "JOGANDO":
                    impulso_pendente = True

        teclas_atuais = pygame.key.get_pressed()
        espaco_pressionado = teclas_atuais[pygame.K_SPACE]
        enter_pressionado = (
            teclas_atuais[pygame.K_RETURN]
            or teclas_atuais[pygame.K_KP_ENTER]
        )
        tecla_iniciar_pressionada = espaco_pressionado or enter_pressionado
        if (
            tecla_iniciar_pressionada
            and not espaco_estava_pressionado
            and estado_jogo in ("MENU", "GAME_OVER")
        ):
            iniciar_partida()
        espaco_estava_pressionado = tecla_iniciar_pressionada

        for _ in range(random.randint(1, 3)):
            particulas_lava.append(criar_particula_lava())

        atualizar_particulas_lava(particulas_lava, dt)

        if estado_jogo == "JOGANDO":
            teclas = pygame.key.get_pressed()
            atualizar_controle_bolinha(ball_body, teclas, dt)

            space.step(dt)

            if impulso_pendente:
                ball_body.activate()
                vx, vy = ball_body.velocity
                ball_body.velocity = (vx, min(vy, -IMPULSO_VERTICAL))
                impulso_pendente = False
                impulso_protecao_frames = IMPULSO_PROTECAO_FRAMES
            elif impulso_protecao_frames > 0:
                ball_body.activate()
                vx, vy = ball_body.velocity
                ball_body.velocity = (vx, min(vy, -IMPULSO_VERTICAL))
                impulso_protecao_frames -= 1

            atualizar_rastro_bolinha(
                rastro_bolinha, ball_body.position, dt
            )
            atualizar_particulas_rastro(
                particulas_rastro,
                ball_body.position,
                ball_body.velocity,
                dt
            )

            if random.random() < FREQUENCIA_FAISCAS_ESTRELA:

                posicao_efeito_estrela = (
                    estrela_pos[0], estrela_pos[1]
                )
                particulas_estrela.append(
                    criar_particula_estrela(posicao_efeito_estrela)
                )

                if random.random() < 0.08:
                    particulas_estrela.append(
                        criar_particula_estrela(posicao_efeito_estrela)
                    )

        atualizar_particulas_estrela(particulas_estrela, dt)

        if estado_jogo == "MENU":
            screen.blit(tela_inicial_img, (0, 0))

            desenhar_particulas_lava(screen, particulas_lava)

            desenhar_botao_principal(screen, "JOGAR", pos_mouse)

        elif estado_jogo == "JOGANDO":
            screen.blit(bg_image, (0, 0))

            desenhar_particulas_lava(screen, particulas_lava)

            draw_pymunk_segments(screen, space)

            desenhar_rastro_bolinha(
                screen,
                superficie_rastro,
                rastro_bolinha,
                particulas_rastro
            )

            x = int(ball_body.position.x)
            y = int(ball_body.position.y)
            radius = int(ball_shape.radius)

            distancia_estrela = math.hypot(
                x - estrela_pos[0], y - estrela_pos[1]
            )
            if distancia_estrela < radius + raio_estrela_jogo:
                pontos += 1
                estrela_pos = gerar_posicao_estrela()

            if y + radius >= LIMITE_LAVA_Y:
                vidas -= 1
                if vidas > 0:
                    resetar_bolinha()
                else:
                    estado_jogo = "GAME_OVER"

            centro_visual_estrela = (
                int(estrela_pos[0]), int(estrela_pos[1])
            )

            superficie_efeitos_estrela.fill((0, 0, 0, 0))
            desenhar_particulas_estrela(
                superficie_efeitos_estrela,
                particulas_estrela
            )
            screen.blit(superficie_efeitos_estrela, (0, 0))

            rect_estrela = estrela_jogo_img.get_rect(
                center=centro_visual_estrela
            )
            screen.blit(estrela_jogo_img, rect_estrela)

            pygame.draw.circle(screen, BALL_COLOR, (x, y), radius)
            pygame.draw.circle(
                screen, (255, 255, 255),
                (x - 4, y - 4), max(2, radius // 3)
            )

            pos_y_paineis = 40
            rect_vidas = ui_panel_img.get_rect(
                center=(WIDTH // 2 - 85, pos_y_paineis)
            )
            desenhar_painel(screen, ui_panel_img, rect_vidas, coracao_img, f"x {vidas}")

            rect_pontos = ui_panel_img.get_rect(
                center=(WIDTH // 2 + 85, pos_y_paineis)
            )
            desenhar_painel(screen, ui_panel_img, rect_pontos, estrela_ui_img, str(pontos))

        elif estado_jogo == "GAME_OVER":
            screen.blit(game_over_img, (0, 0))

            desenhar_particulas_lava(screen, particulas_lava)

            texto_fim = fonte_titulo.render(
                "GAME OVER", True, LAVA_ORANGE_COLOR
            )
            screen.blit(
                texto_fim,
                texto_fim.get_rect(center=(WIDTH // 2, posicao_y_botao - 120)),
            )

            texto_score = fonte_ui.render(f"x {pontos}", True, LIGHT_BLUE_COLOR)
            espaco_icone = 12
            largura_total_score = (
                estrela_jogo_img.get_width() + espaco_icone + texto_score.get_width()
            )
            pos_x_score = (WIDTH // 2) - (largura_total_score // 2)
            pos_y_score = posicao_y_botao - 75

            screen.blit(
                estrela_jogo_img,
                (pos_x_score, pos_y_score - estrela_jogo_img.get_height() // 2),
            )
            screen.blit(
                texto_score,
                (pos_x_score + estrela_jogo_img.get_width() + espaco_icone,
                 pos_y_score - texto_score.get_height() // 2),
            )

            desenhar_botao_principal(screen, "RECOMEÇAR", pos_mouse)

        pygame.display.flip()

if __name__ == "__main__":
    main()