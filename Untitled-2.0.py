"""
=============================================================================
 SNAKE — O JOGO DA COBRINHA  (Python + Pygame)
=============================================================================

 O jogador controla uma cobra que percorre a tela em busca de comida.
 Cada comida normal vale 1 ponto; uma comida DOURADA especial (que surge
 de tempos em tempos e desaparece após 6 segundos) vale 5 pontos.
 A velocidade aumenta conforme os pontos crescem, e o recorde fica salvo
 em um arquivo de texto para as próximas partidas.

 Requisitos da atividade atendidos:
   - Movimentação da cobra pelo teclado (setas ou WASD)
   - Geração de alimentos em posições diferentes da grade
   - Crescimento da cobra ao coletar um alimento
   - Sistema de pontuação (visível na janela do Pygame)
   - Detecção de colisão (com as paredes e com o próprio corpo)
   - Condição de Game Over (tela clara de fim de jogo)
   - Reiniciar a partida após o Game Over sem fechar o programa (ESPAÇO)
   - Código organizado e comentado explicando decisões

 Diferenciais extras implementados:
   - Tela de menu inicial, pausa (tecla P) e tela de Game Over 
   - Comida dourada: vale 5 pontos e tem tempo limite de 6 segundos
   - Velocidade progressiva (a cada ponto a cobra fica um pouco mais rápida)
   - Recorde salvo em arquivo (snake_recorde.txt)
   - Efeitos sonoros gerados pelo próprio código (sem arquivos externos)
   - Cobra com "olhos" que acompanham a direção e corpo com gradiente de cor

 Como executar:
   1) Instale o pygame:      pip install pygame
   2) Salve como:            snake.py
   3) Execute:               python snake.py
=============================================================================
"""

import math          # funções matemáticas (seno, cosseno, pi) p/ sons e desenhos
import os            # caminho do arquivo de recorde
import random        # sorteio de posições para as comidas
import sys           # verificação do tipo de arquitetura (bytes)
from array import array  # buffer de áudio eficiente (16 bits por amostra)

import pygame        # biblioteca gráfica usada no jogo

# =============================================================================
# 1) CONSTANTES GLOBAIS
# -----------------------------------------------------------------------------
# Manter valores "mágicos" em constantes facilita ajustar o jogo depois
# (ex.: mudar o tamanho da grade) sem precisar procurar números pelo código.
# =============================================================================

# Grade lógica: o jogo é dividido em células. A cobra anda de célula em célula.
COLUNAS = 20               # nº de células na horizontal
LINHAS = 20                # nº de células na vertical
TAMANHO_CELULA = 30        # cada célula mede 30 x 30 pixels

LARGURA_JOGO = COLUNAS * TAMANHO_CELULA    # 600 px de área jogável
ALTURA_JOGO = LINHAS * TAMANHO_CELULA      # 600 px de área jogável

ALTURA_HUD = 64            # faixa superior que mostra pontuação/recorde
LARGURA_JANELA = LARGURA_JOGO
ALTURA_JANELA = ALTURA_HUD + ALTURA_JOGO

FPS = 60                   # desenhamos 60 quadros por segundo (animações suaves)

# Cores em RGB (cada valor vai de 0 a 255)
COR_FUNDO_JOGO = (14, 18, 16)      # fundo escuro, estilo "arcade"
COR_GRADE = (25, 32, 28)           # tom dos quadradinhos alternados do tabuleiro
COR_HUD = (19, 26, 22)             # fundo do placar
COR_TEXTO = (235, 240, 235)        # branco esverdeado
COR_TEXTO_FRACO = (150, 165, 155)  # cinza para textos secundários
COR_VERDE_CLARO = (140, 240, 150)  # cor da cabeça da cobra
COR_VERDE_ESCURO = (25, 130, 70)   # cor da cauda (gradiente)
COR_BRANCO = (245, 245, 245)
COR_PRETO = (10, 10, 10)
COR_DOURADO = (255, 205, 60)       # comida especial
COR_DOURADO_CLARO = (255, 238, 150)  # brilho da comida especial
COR_VERMELHO_MAÇA = (235, 70, 70)     # corpo da maçã (comida normal)
COR_VERMELHO_ESCURO = (150, 35, 45)   # contorno/sombra da maçã
COR_BRILHO = (255, 170, 160)          # reflexo de luz na maçã
COR_VERDE_FOLHA = (80, 180, 95)       # folha da maçã
COR_MARROM = (130, 85, 50)            # talo da maçã

# Direções de movimento representadas como vetores de célula.
# Exemplo: DIREITA = (1, 0) significa "anda 1 coluna, 0 linhas por passo".
DIREITA = (1, 0)
ESQUERDA = (-1, 0)
CIMA = (0, -1)
BAIXO = (0, 1)

# Velocidade: controlamos pelo INTERVALO (em milissegundos) entre os passos
# da cobra. Intervalo 160 ms = ~6 passos por segundo; quanto MENOR, MAIS rápida.
INTERVALO_INICIAL_MS = 160       # velocidade inicial
INTERVALO_MINIMO_MS = 60         # limite de velocidade (para o jogo não ficar impossível)
MS_REDUZIDOS_POR_PONTO = 2       # cada ponto ganho reduz 2 ms do intervalo

# Regras da comida dourada
COMIDAS_PARA_DOURADA = 4         # surge após o jogador comer 4 comidas normais
TEMPO_DOURADA_MS = 6000          # some após 6 segundos sem ser comida
PONTOS_DOURADA = 5               # quanto vale a comida dourada

# Estados possíveis do jogo (uma "máquina de estados" simples)
MENU = "menu"                    # tela inicial
JOGANDO = "jogando"              # partida em andamento
PAUSADO = "pausado"              # pausa
GAME_OVER = "game_over"          # fim de partida

# Taxa de amostragem do áudio: nº de amostras por segundo. Quanto maior,
# melhor a qualidade, porém mais memória. 22050 Hz é suficiente p/ efeitos.
TAXA_AMOSTRAGEM = 22050

# Caminho do arquivo onde o recorde será guardado (na mesma pasta do jogo)
CAMINHO_RECORDE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "snake_recorde.txt"
)

# =============================================================================
# 2) GERENCIADOR DE SOM — efeitos gerados matematicamente
# -----------------------------------------------------------------------------
# Em vez de depender de arquivos .wav externos, GERAMOS o áudio na hora:
# calculamos amostra por amostra do valor da onda (seno ou quadrada) e
# entregamos ao pygame um buffer de áudio pronto.
#
# Conceitos usados (ótimos para explicar na aula):
#  - Onda quadrada: valor +1 ou -1 alternando; timbre "retrô" de jogo clássico.
#  - Envelope: multiplicamos a onda por um valor que cai até zero no final
#    do som, evitando "estouros" (cliques) no alto-falante.
#  - Frequência: número de oscilações por segundo (Hz). Quanto maior, mais
#    agudo o som. Variando a frequência ao longo do tempo criamos efeitos
#    como o glissando (som que desce) do Game Over.
# =============================================================================

class GerenciadorSom:
    """Cria e toca os efeitos sonoros do jogo."""

    def __init__(self):
        self.disponivel = False
        # Inicializa objetos de som como None; serão criados se o áudio funcionar
        self.som_comer = None
        self.som_dourada = None
        self.som_game_over = None
        self.som_recorde = None
        self._cache_tons = {}   # cache de tons de "comer" (a frequência muda c/ a pontuação)

        try:
            # Formato do mixer: 22050 Hz, 16 bits com sinal, 1 canal (mono)
            pygame.mixer.init(TAXA_AMOSTRAGEM, -16, 1, 512)
            pygame.mixer.set_num_channels(16)  # até 16 sons simultâneos
        except pygame.error:
            # Sem dispositivo de áudio (ex.: máquina sem som): o jogo roda mudo
            return

        # --- Efeito de comer comida NORMAL: um "blip" curto e agudo ---
        self.som_comer_base = self._gerar_tom(650, 0.07, 0.35)

        # --- Efeito da comida DOURADA: arpejo ascendente (3 notas subindo) ---
        self.som_dourada = pygame.mixer.Sound(buffer=self._compor([
            (880, 0.06), (1175, 0.06), (1568, 0.10)
        ]))

        # --- Game Over: glissando descendente (o tom "escorrega" para baixo) ---
        self.som_game_over = pygame.mixer.Sound(
            buffer=self._gerar_glissando(380, 70, 0.9, 0.45)
        )

        # --- Novo recorde: pequena fanfarra (4 notas, com pausas entre elas) ---
        pausa = self._gerar_silencio(0.04)
        self.som_recorde = pygame.mixer.Sound(buffer=(
            self._gerar_tom(523, 0.09, 0.4) + pausa +
            self._gerar_tom(659, 0.09, 0.4) + pausa +
            self._gerar_tom(784, 0.09, 0.4) + pausa +
            self._gerar_tom(1047, 0.20, 0.45)
        ))

        self.disponivel = True

    # -------------------------------------------------------------------------
    # Geração de áudio
    # -------------------------------------------------------------------------
    def _gerar_tom(self, frequencia, duracao_seg, volume=0.5, forma="quadrada"):
        """Gera os bytes de um tom puro com fade-out suave (sem 'clique')."""
        total = int(TAXA_AMOSTRAGEM * duracao_seg)   # quantas amostras gerar
        amostras = array("h")                        # 'h' = inteiro 16 bits c/ sinal
        for i in range(total):
            tempo = i / TAXA_AMOSTRAGEM              # instante da amostra em segundos
            if forma == "quadrada":
                # Onda quadrada: 1 se o seno for positivo, -1 caso contrário
                valor = 1.0 if math.sin(2 * math.pi * frequencia * tempo) >= 0 else -1.0
            else:  # senoidal pura (mais suave)
                valor = math.sin(2 * math.pi * frequencia * tempo)
            # Envelope: começa em 1 e cai linearmente até 0 no fim do som
            envelope = 1.0 - (i / total)
            # 32767 é o maior valor representável em 16 bits com sinal
            amostras.append(int(32767 * volume * envelope * valor))
        if sys.byteorder != "little":
            amostras.byteswap()  # garante o formato correto em qualquer máquina
        return amostras.tobytes()

    def _gerar_glissando(self, freq_inicial, freq_final, duracao_seg, volume):
        """Gera um tom cuja frequência desliza de freq_inicial até freq_final."""
        total = int(TAXA_AMOSTRAGEM * duracao_seg)
        amostras = array("h")
        for i in range(total):
            fracao = i / total                         # 0 no início, 1 no fim
            frequencia = freq_inicial + (freq_final - freq_inicial) * fracao
            tempo = i / TAXA_AMOSTRAGEM
            valor = 1.0 if math.sin(2 * math.pi * frequencia * tempo) >= 0 else -1.0
            envelope = 1.0 - fracao                    # fade-out
            amostras.append(int(32767 * volume * envelope * valor))
        if sys.byteorder != "little":
            amostras.byteswap()
        return amostras.tobytes()

    def _gerar_silencio(self, duracao_seg):
        """Gera um trecho de silêncio (zeros) — usado entre notas de melodias."""
        return b"\x00" * int(TAXA_AMOSTRAGEM * duracao_seg * 2)

    def _compor(self, notas):
        """Concatena vários tons em um único áudio (notas: lista de (freq, dur))."""
        return b"".join(
            self._gerar_tom(freq, dur, 0.4) for freq, dur in notas
        )

    # -------------------------------------------------------------------------
    # Reprodução
    # -------------------------------------------------------------------------
    def tocar_comer(self, frequencia=650):
        """Toca o 'blip' de comida. A frequência pode variar conforme a pontuação
        (o som fica mais agudo conforme o jogador evolui)."""
        if not self.disponivel:
            return
        # Cache: cria o Sound só na primeira vez que aquela frequência é usada
        if frequencia not in self._cache_tons:
            self._cache_tons[frequencia] = pygame.mixer.Sound(
                buffer=self._gerar_tom(frequencia, 0.07, 0.35)
            )
        self._cache_tons[frequencia].play()

    def tocar_dourada(self):
        if self.disponivel and self.som_dourada is not None:
            self.som_dourada.play()

    def tocar_game_over(self):
        if self.disponivel and self.som_game_over is not None:
            self.som_game_over.play()

    def tocar_recorde(self):
        if self.disponivel and self.som_recorde is not None:
            self.som_recorde.play()

# =============================================================================
# 3) CLASSE COBRA
# -----------------------------------------------------------------------------
# Como o jogo é baseado em grade, a cobra é apenas uma LISTA de posições
# (coluna, linha). O primeiro elemento da lista é a CABEÇA; os demais são o
# corpo. Crescer = acrescentar um segmento na frente e NÃO remover a cauda.
# =============================================================================

class Cobra:
    def __init__(self, posicao_inicial):
        # posicao_inicial é uma lista de tuplas: a cobra nasce com 3 segmentos
        self.segmentos = list(posicao_inicial)
        self.direcao = DIREITA            # direção ATUAL (já aplicada)
        self.direcao_pendente = None      # direção que o jogador pediu (a aplicar)

    @property
    def cabeca(self):
        """A cabeça é sempre o primeiro segmento da lista."""
        return self.segmentos[0]

    @property
    def direcao_efetiva(self):
        """Direção que valerá no PRÓXIMO passo (a pendente, se existir).

        Usamos esse conceito para que a validação de colisão e o movimento
        usem exatamente a mesma direção — evitando "bugs de teleporte".
        """
        return self.direcao_pendente if self.direcao_pendente is not None else self.direcao

    def definir_direcao(self, nova_direcao):
        """Registra a direção desejada, impedindo que a cobra 'dê ré'.

        A cobra não pode ir para a direção OPOSTA à que está se movendo
        (ou à pendente), pois isso a faria atravessar o próprio corpo.
        """
        base = self.direcao_pendente if self.direcao_pendente is not None else self.direcao
        # Reversão seria: (dx2, dy2) == (-dx1, -dy1)
        if (nova_direcao[0], nova_direcao[1]) == (-base[0], -base[1]):
            return
        if nova_direcao == base:   # mesma direção: nada a fazer
            return
        self.direcao_pendente = nova_direcao

    def avancar(self, crescer):
        """Move a cobra um passo. Se crescer=True, a cauda é mantida na lista
        (a cobra fica 1 segmento maior); caso contrário, a cauda 'anda' junto."""
        if self.direcao_pendente is not None:
            self.direcao = self.direcao_pendente   # aplica a virada pedida
            self.direcao_pendente = None
        col, lin = self.cabeca
        dx, dy = self.direcao
        nova_cabeca = (col + dx, lin + dy)
        self.segmentos.insert(0, nova_cabeca)   # nova cabeça entra na frente
        if not crescer:
            self.segmentos.pop()                # sem crescer, a cauda sai

# =============================================================================
# 4) CLASSE COMIDA
# -----------------------------------------------------------------------------
# Representa um alimento na grade. O campo 'normal' define se vale 1 ponto
# (maçã vermelha) ou 5 pontos (estrela dourada). A comida nunca pode nascer
# sobre a cobra ou sobre outra comida, por isso usamos 'celulas_ocupadas'.
# =============================================================================

class Comida:
    def __init__(self, normal=True):
        self.posicao = None        # tupla (coluna, linha) ou None se não existir
        self.normal = normal

    def reposicionar(self, celulas_ocupadas):
        """Sorteia uma célula livre da grade. Retorna False se não houver espaço
        (caso em que a cobra preencheu a tela inteira — vitória!)."""
        livres = [
            (c, l)
            for c in range(COLUNAS)
            for l in range(LINHAS)
            if (c, l) not in celulas_ocupadas
        ]
        if not livres:
            self.posicao = None
            return False
        self.posicao = random.choice(livres)   # escolha aleatória entre as livres
        return True

    def centro_em_pixels(self):
        """Converte a posição de célula para o CENTRO (em pixels) da célula.
        Lembrando que a área jogável começa logo abaixo do HUD."""
        col, lin = self.posicao
        x = col * TAMANHO_CELULA + TAMANHO_CELULA // 2
        y = ALTURA_HUD + lin * TAMANHO_CELULA + TAMANHO_CELULA // 2
        return x, y

# =============================================================================
# 5) CLASSE JOGO — controla todo o fluxo do programa
# -----------------------------------------------------------------------------
# O jogo segue o padrão clássico de um loop de jogo:
#   1. processar eventos (teclado, fechar janela)
#   2. atualizar a lógica (mover cobra, colisões, temporizadores)
#   3. desenhar tudo na tela
# Esse ciclo se repete ~60 vezes por segundo enquanto o jogo roda.
#
# A máquina de estados (MENU -> JOGANDO -> GAME_OVER -> ...) organiza o que
# pode acontecer em cada momento: só se move durante JOGANDO, só se reinicia
# apertando ESPAÇO em MENU ou GAME_OVER etc.
# =============================================================================

class Jogo:
    def __init__(self):
        # pre_init define o formato do áudio ANTES do pygame.init() — é o
        # jeito recomendado para o mixer já nascer configurado
        pygame.mixer.pre_init(TAXA_AMOSTRAGEM, -16, 1, 512)
        pygame.init()

        self.tela = pygame.display.set_mode((LARGURA_JANELA, ALTURA_JANELA))
        pygame.display.set_caption("Snake — Jogo da Cobrinha")

        self.relogio = pygame.time.Clock()   # controla os FPS

        # Fontes (com alternativas separadas por vírgula: usa a 1ª disponível)
        self.fonte_placar = pygame.font.SysFont("consolas,monospace,arial", 22, bold=True)
        self.fonte_titulo = pygame.font.SysFont("consolas,monospace,arial", 58, bold=True)
        self.fonte_media = pygame.font.SysFont("consolas,monospace,arial", 30, bold=True)
        self.fonte_pequena = pygame.font.SysFont("consolas,monospace,arial", 18)

        self.som = GerenciadorSom()
        self.recorde = self._carregar_recorde()   # recorde vindo do arquivo
        self.rodando = True
        self.estado = MENU
        self.reset()   # prepara uma partida nova (a cobra já fica desenhada no menu)

    # -------------------------------------------------------------------------
    # 5.1) Preparação de uma partida nova
    # -------------------------------------------------------------------------
    def reset(self):
        """Reinicia todos os valores para começar uma partida do zero."""
        # Cobra nasce no centro, com 3 segmentos, andando para a direita
        centro_col = COLUNAS // 2
        centro_lin = LINHAS // 2
        self.cobra = Cobra([
            (centro_col, centro_lin),
            (centro_col - 1, centro_lin),
            (centro_col - 2, centro_lin),
        ])

        self.pontos = 0
        self.venceu = False                    # True se a cobra lotar a tela
        self.novo_recorde = False              # usado para avisar na tela final

        # Comida normal: uma maçã sempre presente no tabuleiro
        self.comida = Comida(normal=True)
        self.comida.reposicionar(self._celulas_ocupadas())

        # Comida dourada: começa inexistente
        self.comida_dourada = None
        self.comidas_desde_dourada = 0         # contador p/ decidir quando ela surge
        self.tempo_dourada_restante = 0        # tempo que ainda falta p/ ela sumir

        # Controle de tempo do movimento da cobra
        self._acumulado = 0                    # tempo acumulado desde o último passo
        self._referencia_tempo = pygame.time.get_ticks()

    def _celulas_ocupadas(self):
        """Conjunto de células ocupadas (cobra + comidas). Usado para sortear
        posições livres SEM sobreposição."""
        ocupadas = set(self.cobra.segmentos)
        if self.comida.posicao is not None:
            ocupadas.add(self.comida.posicao)
       # if self.comida_dourada is not None and self.comida_dourada.posicao is not None:
           # ocupadas.add(self.comida_dourada.posicao)
        return ocupadas

    def _intervalo_atual(self):
        """Intervalo (ms) entre os passos da cobra, conforme a pontuação.
        Quanto mais pontos, menor o intervalo => cobra mais rápida."""
        return max(
            INTERVALO_MINIMO_MS,
            INTERVALO_INICIAL_MS - self.pontos * MS_REDUZIDOS_POR_PONTO,
        )

    def _velocidade_por_segundo(self):
        """Passos por segundo (só para exibir no HUD)."""
        return int(round(1000 / self._intervalo_atual()))

    # -------------------------------------------------------------------------
    # 5.2) Recorde salvo em arquivo
    # -------------------------------------------------------------------------
    @staticmethod
    def _carregar_recorde():
        """Lê o recorde do arquivo. Se o arquivo não existir ou estiver
        corrompido, retorna 0 (o jogo simplesmente começa sem recorde)."""
        try:
            with open(CAMINHO_RECORDE, "r", encoding="utf-8") as arquivo:
                return int(arquivo.read().strip())
        except (OSError, ValueError):
            return 0

    @staticmethod
    def _salvar_recorde(valor):
        """Grava o recorde no arquivo. Falhas de escrita são ignoradas para
        não quebrar o jogo (ex.: pasta sem permissão)."""
        try:
            with open(CAMINHO_RECORDE, "w", encoding="utf-8") as arquivo:
                arquivo.write(str(valor))
        except OSError:
            pass

    # -------------------------------------------------------------------------
    # 5.3) Eventos (teclado e janela)
    # -------------------------------------------------------------------------
    def processar_eventos(self):
        """Lê todos os eventos que aconteceram desde o último quadro."""
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:      # usuário clicou no "X" da janela
                self.rodando = False
            elif evento.type == pygame.KEYDOWN:
                self._tratar_tecla(evento.key)

    def _tratar_tecla(self, tecla):
        """Define o que cada tecla faz, dependendo do estado atual do jogo."""
        if tecla == pygame.K_ESCAPE:
            self.rodando = False
            return

        # Pausa (P) só faz sentido durante uma partida
        if tecla == pygame.K_p and self.estado in (JOGANDO, PAUSADO):
            self.estado = PAUSADO if self.estado == JOGANDO else JOGANDO
            # Ao voltar do pause, reinicia a referência de tempo para o jogo
            # não "pular" vários movimentos de uma vez (o tempo parou pausado)
            self._referencia_tempo = pygame.time.get_ticks()
            return

        # ESPAÇO começa a partida (no menu) ou reinicia (após game over)
        if tecla == pygame.K_SPACE and self.estado in (MENU, GAME_OVER):
            self.reset()
            self.estado = JOGANDO
            return

        # As teclas de direção só importam durante a partida
        if self.estado != JOGANDO:
            return

        if tecla in (pygame.K_UP, pygame.K_w):
            self.cobra.definir_direcao(CIMA)
        elif tecla in (pygame.K_DOWN, pygame.K_s):
            self.cobra.definir_direcao(BAIXO)
        elif tecla in (pygame.K_LEFT, pygame.K_a):
            self.cobra.definir_direcao(ESQUERDA)
        elif tecla in (pygame.K_RIGHT, pygame.K_d):
            self.cobra.definir_direcao(DIREITA)

    # -------------------------------------------------------------------------
    # 5.4) Atualização da lógica (chamada apenas no estado JOGANDO)
    # -------------------------------------------------------------------------
    def atualizar(self):
        agora = pygame.time.get_ticks()
        dt = agora - self._referencia_tempo    # milissegundos desde o último quadro
        self._referencia_tempo = agora

        # --- Movimento da cobra no ritmo da velocidade atual ---
        # Em vez de mover a cada quadro (60x/s), acumulamos o tempo e movemos
        # somente quando o acumulado ultrapassa o intervalo atual. Isso garante
        # velocidade constante, independente de oscilações de FPS.
        self._acumulado += dt
        while self._acumulado >= self._intervalo_atual():
            self._acumulado -= self._intervalo_atual()
            if not self._mover_cobra():        # False = colidiu => fim de jogo
                self._finalizar_partida()
                return

        # --- Temporizador da comida dourada: se o tempo esgotar, ela some ---
        if self.comida_dourada is not None:
            self.tempo_dourada_restante -= dt
            if self.tempo_dourada_restante <= 0:
                self.comida_dourada = None     # o jogador perdeu a chance

    def _mover_cobra(self):
        """Dá UM passo na cobra, aplicando colisões. Retorna True se ela
        sobreviveu, ou False se bateu na parede / no próprio corpo."""
        dx, dy = self.cobra.direcao_efetiva
        col, lin = self.cobra.cabeca
        nova_cabeca = (col + dx, lin + dy)

        # 1) Colisão com as PAREDES: a nova cabeça saiu da área jogável?
        if not (0 <= nova_cabeca[0] < COLUNAS and 0 <= nova_cabeca[1] < LINHAS):
            return False

        # 2) A cobra vai crescer se pisar em alguma comida?
        comeu_normal = self.comida.posicao == nova_cabeca
        comeu_dourada = (
            self.comida_dourada is not None
            and self.comida_dourada.posicao == nova_cabeca
        )
        crescer = comeu_normal or comeu_dourada

        # 3) Colisão com o PRÓPRIO CORPO. Detalhe importante: se a cobra NÃO
        #    vai crescer, a cauda se desloca no mesmo passo — então ela não é
        #    obstáculo (por isso checamos segmentos[:-1], ignorando a cauda).
        corpo_obstaculo = self.cobra.segmentos if crescer else self.cobra.segmentos[:-1]
        if nova_cabeca in corpo_obstaculo:
            return False

        # 4) Movimento efetivo (e crescimento, se for o caso)
        self.cobra.avancar(crescer)

        # 5) Consequências de ter comido
        if comeu_normal:
            self.pontos += 1
            # O "blip" fica mais agudo conforme o jogador pontua (feedback sonoro)
            self.som.tocar_comer(500 + min(self.pontos, 60) * 5)
            self.comidas_desde_dourada += 1
            if not self.comida.reposicionar(self._celulas_ocupadas()):
                self.venceu = True            # não há mais espaço p/ comida!
                return False                  # encerra a partida (vitória)
            # A cada X comidas normais, a comida dourada aparece (se houver espaço)
            if self.comidas_desde_dourada >= COMIDAS_PARA_DOURADA:
                self.comidas_desde_dourada = 0
                self._surgir_dourada()
        elif comeu_dourada:
            self.pontos += PONTOS_DOURADA
            self.som.tocar_dourada()
            self.comida_dourada = None        # foi comida: some do tabuleiro
            self.comidas_desde_dourada = 0

        return True

    def _surgir_dourada(self):
        """Cria a comida dourada em uma célula livre e inicia o seu cronômetro."""
        dourada = Comida(normal=False)
        if dourada.reposicionar(self._celulas_ocupadas()):
            self.comida_dourada = dourada
            self.tempo_dourada_restante = TEMPO_DOURADA_MS

    def _finalizar_partida(self):
        """Aplica as consequências do fim de jogo (game over ou vitória)."""
        self.estado = GAME_OVER
        if self.pontos > self.recorde:
            self.recorde = self.pontos         # atualiza o recorde em memória
            self.novo_recorde = True
            self._salvar_recorde(self.recorde) # ... e no arquivo
            self.som.tocar_recorde()           # fanfarra de novo recorde
        else:
            self.som.tocar_game_over()

    # -------------------------------------------------------------------------
    # 5.5) Desenho
    # -------------------------------------------------------------------------
    def desenhar(self):
        """Desenha um quadro completo na tela."""
        self._tempo = pygame.time.get_ticks()   # usado nas animações

        # 1) Fundo + HUD (placar) — sempre visíveis
        self.tela.fill(COR_FUNDO_JOGO)
        self._desenhar_hud()

        # 2) Área do jogo (grade, comidas e cobra)
        self._desenhar_area_jogo()

        # 3) Camadas de texto conforme o estado
        if self.estado == MENU:
            self._desenhar_menu()
        elif self.estado == PAUSADO:
            self._desenhar_aviso_pausa()
        elif self.estado == GAME_OVER:
            self._desenhar_game_over()

        pygame.display.flip()   # envia o quadro desenhado para a janela

    def _desenhar_area_jogo(self):
        """Desenha o tabuleiro (padrão xadrez suave), as comidas e a cobra."""
        # Quadradinhos alternados: dão sensação de "tabuleiro" e ajudam a
        # enxergar a grade (e os movimentos de célula em célula)
        for col in range(COLUNAS):
            for lin in range(LINHAS):
                if (col + lin) % 2 == 0:
                    pygame.draw.rect(
                        self.tela, COR_GRADE,
                        (col * TAMANHO_CELULA,
                         ALTURA_HUD + lin * TAMANHO_CELULA,
                         TAMANHO_CELULA, TAMANHO_CELULA),
                    )

        self._desenhar_comida_normal()
        self._desenhar_comida_dourada()
        self._desenhar_cobra()

    def _desenhar_cobra(self):
        """Desenha a cobra com gradiente de cor e olhos que seguem a direção."""
        total = len(self.cobra.segmentos)
        for indice, (col, lin) in enumerate(self.cobra.segmentos):
            # Interpola a cor entre verde-claro (cabeça) e verde-escuro (cauda)
            fracao = indice / max(1, total - 1)
            cor = (
                int(COR_VERDE_CLARO[0] + (COR_VERDE_ESCURO[0] - COR_VERDE_CLARO[0]) * fracao),
                int(COR_VERDE_CLARO[1] + (COR_VERDE_ESCURO[1] - COR_VERDE_CLARO[1]) * fracao),
                int(COR_VERDE_CLARO[2] + (COR_VERDE_ESCURO[2] - COR_VERDE_CLARO[2]) * fracao),
            )
            # Cada segmento é um quadrado com 1px de margem e cantos suaves
            x = col * TAMANHO_CELULA + 1
            y = ALTURA_HUD + lin * TAMANHO_CELULA + 1
            raio_canto = 8 if indice == 0 else 6   # cabeça com cantos mais redondos
            pygame.draw.rect(self.tela, cor, (x, y, TAMANHO_CELULA - 2, TAMANHO_CELULA - 2),
                             border_radius=raio_canto)

        self._desenhar_olhos()

    def _desenhar_olhos(self):
        """Dois olhos na cabeça que se reposicionam conforme a direção.

        Ideia: partimos do centro da cabeça e deslocamos cada olho um pouco
        para FRENTE (na direção do movimento) e um pouco para os LADOS
        (usando um vetor perpendicular à direção)."""
        col, lin = self.cobra.cabeca
        cx = col * TAMANHO_CELULA + TAMANHO_CELULA // 2
        cy = ALTURA_HUD + lin * TAMANHO_CELULA + TAMANHO_CELULA // 2
        dx, dy = self.cobra.direcao
        # Vetor perpendicular à direção (gira (dx, dy) em 90°)
        perp_x, perp_y = -dy, dx

        for lado in (-1, 1):   # olho esquerdo (-1) e direito (+1)
            ox = cx + dx * 3.5 + perp_x * lado * 4.0
            oy = cy + dy * 3.5 + perp_y * lado * 4.0
            pygame.draw.circle(self.tela, COR_BRANCO, (int(ox), int(oy)), 5)
            # Pupila deslocada na direção do movimento (dá vida ao olhar)
            pygame.draw.circle(self.tela, COR_PRETO, (int(ox + dx * 2.2), int(oy + dy * 2.2)), 2)

    def _desenhar_comida_normal(self):
        """Desenha a maçã (1 ponto) usando formas geométricas simples."""
        if self.comida.posicao is None:
            return
        cx, cy = self.comida.centro_em_pixels()

        # Sombra (círculo vermelho-escuro levemente deslocado)
        pygame.draw.circle(self.tela, COR_VERMELHO_ESCURO, (cx + 2, cy + 3), 12)
        # Corpo da maçã
        pygame.draw.circle(self.tela, COR_VERMELHO_MAÇA, (cx, cy), 11)
        # Reflexo de luz (círculo pequeno no topo-esquerdo)
        pygame.draw.circle(self.tela, COR_BRILHO, (cx - 4, cy - 4), 3)
        # Talo (retângulo marrom)
        pygame.draw.rect(self.tela, COR_MARROM, (cx - 1, cy - 14, 3, 6))
        # Folha (elipse verde)
        pygame.draw.ellipse(self.tela, COR_VERDE_FOLHA, (cx + 1, cy - 16, 9, 5))

    def _desenhar_comida_dourada(self):
        """Desenha a estrela dourada (5 pontos) com pulso, rotação e um anel
        que mostra quanto tempo ainda resta antes de ela sumir."""
        if self.comida_dourada is None or self.comida_dourada.posicao is None:
            return
        cx, cy = self.comida_dourada.centro_em_pixels()
        tempo = self._tempo

        # A estrela é um polígono de 10 vértices: 5 externos (raio maior)
        # alternados com 5 internos (raio menor). O raio pulsa com o seno do
        # tempo e a estrela gira lentamente — efeito de "item especial".
        raio_externo = 13 + math.sin(tempo * 0.01) * 1.5
        raio_interno = raio_externo * 0.45
        giro = tempo * 0.001
        pontos = []
        for i in range(10):
            angulo = giro + i * math.pi / 5 - math.pi / 2
            raio = raio_externo if i % 2 == 0 else raio_interno
            pontos.append((cx + raio * math.cos(angulo), cy + raio * math.sin(angulo)))
        pygame.draw.polygon(self.tela, COR_DOURADO, pontos)
        # Brilho central
        pygame.draw.circle(self.tela, COR_DOURADO_CLARO, (cx, cy), 4)

        # Anel de tempo restante: círculo completo em cinza + arco dourado
        # proporcional ao tempo que ainda falta (o arco "encolhe" com o tempo)
        retangulo_anel = (cx - 17, cy - 17, 34, 34)
        pygame.draw.arc(self.tela, COR_GRADE, retangulo_anel, 0, 2 * math.pi, 3)
        fracao_restante = max(0.0, self.tempo_dourada_restante / TEMPO_DOURADA_MS)
        angulo_final = -math.pi / 2 + 2 * math.pi * fracao_restante
        pygame.draw.arc(
            self.tela, COR_DOURADO_CLARO, retangulo_anel,
            -math.pi / 2, angulo_final, 3,
        )

    def _desenhar_hud(self):
        """Placar no topo: pontos, recorde, velocidade e aviso da dourada."""
        # Fundo do HUD
        pygame.draw.rect(self.tela, COR_HUD, (0, 0, LARGURA_JANELA, ALTURA_HUD))
        pygame.draw.line(self.tela, COR_GRADE, (0, ALTURA_HUD), (LARGURA_JANELA, ALTURA_HUD), 2)

        # Pontos à esquerda
        self._escrever_texto(
            f"PONTOS: {self.pontos}", self.fonte_placar, COR_TEXTO,
            (16, ALTURA_HUD // 2), alinhar="esquerda",
        )
        # Recorde à direita
        self._escrever_texto(
            f"RECORDE: {self.recorde}", self.fonte_placar, COR_TEXTO,
            (LARGURA_JANELA - 16, ALTURA_HUD // 2), alinhar="direita",
        )
        # Velocidade no centro-superior
        self._escrever_texto(
            f"VELOCIDADE: {self._velocidade_por_segundo()} PASSOS/S",
            self.fonte_pequena, COR_TEXTO_FRACO,
            (LARGURA_JANELA // 2, 14), alinhar="centro",
        )
        # Aviso da comida dourada ativa (piscando), centro-inferior
        if self.comida_dourada is not None and self.estado in (JOGANDO, PAUSADO):
            if (self._tempo // 400) % 2 == 0:
                segundos = max(0, self.tempo_dourada_restante // 1000)
                self._escrever_texto(
                    f"DOURADA ATIVA: {segundos}s!", self.fonte_pequena, COR_DOURADO,
                    (LARGURA_JANELA // 2, 44), alinhar="centro",
                )

    # -------------------------------------------------------------------------
    # 5.6) Telas de texto (menu, pausa e game over)
    # -------------------------------------------------------------------------
    def _escrever_texto(self, texto, fonte, cor, centro, alinhar="centro"):
        """Renderiza um texto e o posiciona. Retorna o retângulo ocupado."""
        superficie = fonte.render(texto, True, cor)
        rect = superficie.get_rect()
        if alinhar == "esquerda":
            rect.midleft = centro
        elif alinhar == "direita":
            rect.midright = centro
        else:
            rect.center = centro
        self.tela.blit(superficie, rect)
        return rect

    def _sobrepor_area(self, alpha=150):
        """Cria uma camada escura semi-transparente sobre a área do jogo,
        para dar destaque aos textos (menu, pausa, game over)."""
        camada = pygame.Surface((LARGURA_JOGO, ALTURA_JOGO), pygame.SRCALPHA)
        camada.fill((0, 0, 0, alpha))
        self.tela.blit(camada, (0, ALTURA_HUD))

    def _centro_area(self):
        """Ponto central da área jogável (referência para posicionar textos)."""
        return (LARGURA_JOGO // 2, ALTURA_HUD + ALTURA_JOGO // 2)

    def _desenhar_menu(self):
        self._sobrepor_area(150)
        cx, cy = self._centro_area()

        # Título
        self._escrever_texto("SNAKE", self.fonte_titulo, COR_VERDE_CLARO, (cx, cy - 150))
        self._escrever_texto("Jogo da Cobrinha em Python + Pygame",
                             self.fonte_pequena, COR_TEXTO_FRACO, (cx, cy - 105))

        # Instruções
        y = cy - 45
        instrucoes = [
            "SETAS OU WASD PARA MOVER",
            "P PAUSA  |  ESC SAI",
            "",
            "COMIDA NORMAL (MAC[A]): 1 PONTO",
            "COMIDA DOURADA (ESTRELA): 5 PONTOS",
            "A DOURADA SURGE A CADA 4 COMIDAS E SOME EM 6 SEGUNDOS",
            "",
            f"RECORDE ATUAL: {self.recorde}",
        ]
        for linha in instrucoes:
            if linha:
                self._escrever_texto(linha, self.fonte_pequena, COR_TEXTO,
                                     (cx, y), alinhar="centro")
            y += 28

        # Texto "aperte espaço" piscando
        if (self._tempo // 500) % 2 == 0:
            self._escrever_texto("PRESSIONE ESPACO PARA COMECAR",
                                 self.fonte_media, COR_DOURADO, (cx, cy + 150))

    def _desenhar_aviso_pausa(self):
        self._sobrepor_area(140)
        cx, cy = self._centro_area()
        self._escrever_texto("PAUSADO", self.fonte_media, COR_TEXTO, (cx, cy - 20))
        self._escrever_texto("Pressione P para continuar",
                             self.fonte_pequena, COR_TEXTO_FRACO, (cx, cy + 20))

    def _desenhar_game_over(self):
        self._sobrepor_area(165)
        cx, cy = self._centro_area()

        # Título principal: GAME OVER (vermelho) ou vitória (verde)
        if self.venceu:
            titulo, cor_titulo = "VOCE VENCEU!", COR_DOURADO
        else:
            titulo, cor_titulo = "GAME OVER", COR_VERMELHO_MAÇA
        self._escrever_texto(titulo, self.fonte_titulo, cor_titulo, (cx, cy - 90))

        # Aviso de novo recorde (piscando, em dourado)
        if self.novo_recorde and (self._tempo // 400) % 2 == 0:
            self._escrever_texto("NOVO RECORDE!", self.fonte_media, COR_DOURADO, (cx, cy - 25))

        # Resumo da partida
        self._escrever_texto(f"PONTOS: {self.pontos}",
                             self.fonte_media, COR_TEXTO, (cx, cy + 30))
        self._escrever_texto(f"RECORDE: {self.recorde}",
                             self.fonte_placar, COR_TEXTO_FRACO, (cx, cy + 70))

        # Como reiniciar / sair
        self._escrever_texto("ESPACO: JOGAR NOVAMENTE",
                             self.fonte_placar, COR_VERDE_CLARO, (cx, cy + 130))
        self._escrever_texto("ESC: SAIR",
                             self.fonte_pequena, COR_TEXTO_FRACO, (cx, cy + 165))

    # -------------------------------------------------------------------------
    # 5.7) Loop principal do jogo
    # -------------------------------------------------------------------------
    def executar(self):
        """Loop infinito que mantém o jogo rodando até o usuário sair."""
        while self.rodando:
            self.processar_eventos()          # 1) o que o usuário apertou?
            if self.estado == JOGANDO:
                self.atualizar()              # 2) atualiza a lógica do jogo
            self.desenhar()                   # 3) desenha o quadro
            self.relogio.tick(FPS)            # espera para manter 60 FPS
        pygame.quit()                         # encerra o pygame com segurança

# =============================================================================
# 6) PONTO DE ENTRADA DO PROGRAMA
# =============================================================================

if __name__ == "__main__":
    jogo = Jogo()
    jogo.executar()