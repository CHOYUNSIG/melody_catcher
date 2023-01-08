
import numpy as np
import pyaudio
import pygame
import time
import win32api
import win32gui


# 매개변수

TITLE = "Melody Catcher"

RATE = 44100
CHUNK = 1024 * 4

FPS = 60

HEIGHT_STATE = 30

WIDTH = 960
HEIGHT = HEIGHT_STATE+540

FREQ_MASK = 15

GRAPH_AUDIO_CY = 100
GRAPH_AUDIO_X = 20
GRAPH_AUDIO_Y = HEIGHT - GRAPH_AUDIO_CY - 30
GRAPH_AUDIO_CX = WIDTH - GRAPH_AUDIO_X * 2

PEAK_HOLD = 1
PEAK_REALESE = 0.5

# 프로세스 레퍼런스
HWND = None

pygame.init()
pygame.display.set_caption(TITLE)
pygame.display.set_icon(pygame.image.load("img/icon_mc.png"))
clock = pygame.time.Clock()
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.NOFRAME)

text = []
text.append(pygame.font.Font("font/Pretendard-Thin.otf", 15).render("Melody Catcher", True, (255,255,255)))
text.append(pygame.font.Font("font/Pretendard-Thin.otf", 25).render("Audio signal", True, (255,255,255)))
text.append(pygame.font.Font("font/Pretendard-Thin.otf", 25).render("Spectrogram", True, (255,255,255)))
text.append(pygame.transform.rotate(pygame.font.Font("font/Pretendard-Regular.otf", 10).render("20Hz", True, (255,255,255)), 315))
text.append(pygame.transform.rotate(pygame.font.Font("font/Pretendard-Regular.otf", 10).render("100Hz", True, (255,255,255)), 315))
text.append(pygame.transform.rotate(pygame.font.Font("font/Pretendard-Regular.otf", 10).render("1kHz", True, (255,255,255)), 315))
text.append(pygame.transform.rotate(pygame.font.Font("font/Pretendard-Regular.otf", 10).render("10kHz", True, (255,255,255)), 315))
text.append(pygame.transform.rotate(pygame.font.Font("font/Pretendard-Regular.otf", 10).render("20kHz", True, (255,255,255)), 315))
text.append(pygame.font.Font("font/Pretendard-Regular.otf", 10).render("Sample start", True, (0,255,0)))
text.append(pygame.font.Font("font/Pretendard-Regular.otf", 10).render("Sample end", True, (255,0,0)))
text.append(pygame.font.Font("font/Pretendard-Regular.otf", 10).render("Raw", True, (255,255,255)))
text.append(pygame.font.Font("font/Pretendard-Regular.otf", 10).render("A-weighting", True, (255,255,255)))
text.append(pygame.font.Font("font/Pretendard-Thin.otf", 25).render("Melody", True, (255,255,255)))


win_x = None
win_y = None
mouseprepos = win32api.GetCursorPos()
mouse = win32api.GetCursorPos()
keyboardpre = pygame.key.get_pressed()
keyboard = pygame.key.get_pressed()

eventKey_capture = False
eventKey_disableWindow = False
eventKey_moveWindow = False
eventKey_quit = False

from audio_importer import audio_importer
importer = audio_importer(RATE, FPS, CHUNK)

draw_audio_x = [GRAPH_AUDIO_X+int(np.round(GRAPH_AUDIO_CX*i/CHUNK)) for i in range(CHUNK)]

peak = 0
peak_fresh = 0

pygame.display.flip()

# 프로세스 레퍼런스 업데이트
def callback(hwnd, extra):
    if win32gui.GetWindowText(hwnd) == TITLE:
        global HWND
        HWND = hwnd
win32gui.EnumWindows(callback, None)

win_x, win_y, _, _= win32gui.GetWindowRect(HWND)


while not eventKey_quit:

    clock.tick(FPS)

    # 이벤트 불러오기
    mouse = win32api.GetCursorPos()
    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            eventKey_quit = True

        # 키보드 이벤트
        elif event.type == pygame.KEYDOWN:
            keyboard = pygame.key.get_pressed()
            # ESC
            if keyboard[pygame.K_ESCAPE]:
                eventKey_quit = True
            # SPACEBAR
            if keyboard[pygame.K_SPACE] and not keyboardpre[pygame.K_SPACE]:
                eventKey_capture = not eventKey_capture

        elif event.type == pygame.KEYUP:
            keyboard = pygame.key.get_pressed()

        # 마우스 이벤트
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # 창 이동
            if win_x <= mouse[0] <= win_x + WIDTH - 120 and win_y <= mouse[1] <= win_y + 30:
                eventKey_moveWindow = True

        elif event.type == pygame.MOUSEBUTTONUP:
            if eventKey_moveWindow:    
                eventKey_moveWindow = False
            # 닫기 버튼
            if win_x + WIDTH - 40 <= mouse[0] <= win_x + WIDTH and win_y + 0 <= mouse[1] <= win_y + 30:
                eventKey_quit = True
            # 최소화 버튼
            if win_x + WIDTH - 80 <= mouse[0] <= win_x + WIDTH - 40 and win_y + 0 <= mouse[1] <= win_y + 30:
                eventKey_disableWindow = True
                win32gui.ShowWindow(HWND, 6)
            # 캡처 버튼
            if win_x + WIDTH - 120 <= mouse[0] <= win_x + WIDTH - 80 and win_y + 0 <= mouse[1] <= win_y + 30:
                eventKey_capture = not eventKey_capture

    # 창 활성화    
    if eventKey_disableWindow:
        if win32gui.GetWindowRect(HWND)[0] >= -WIDTH:
            win32gui.ShowWindow(HWND, 9)
            eventKey_disableWindow = False

    # 창 이동
    if eventKey_moveWindow:
        win32gui.SetWindowPos(HWND, 0, win_x+mouse[0]-mouseprepos[0], win_y+mouse[1]-mouseprepos[1], WIDTH, HEIGHT, 64)
        win_x, win_y, _, _ = win32gui.GetWindowRect(HWND)

    # 이전 프레임 데이터 보관처리
    keyboardpre = keyboard
    mouseprepos = mouse

    # 데이터 가공

    # 오디오 데이터 불러오기
    audio_data = importer.get_audio_data()
    importer.importer()
    
    # 헤드룸 조정
    if peak < max(abs(audio_data)) :
        peak = max(abs(audio_data))
        peak_pre = peak
        peak_fresh = time.time()
    elif time.time() - peak_fresh > PEAK_HOLD:
        peak = max(max(abs(audio_data)), peak - peak/PEAK_REALESE/FPS)

    # 화면 구성

    if not eventKey_capture:

        # 배경
        for i in range(HEIGHT):
            pygame.draw.line(screen, (70, int(70-i/HEIGHT*70), int(100-i/HEIGHT*70)), [0,i], [WIDTH, i], 2)
        
        # 메인

        # 오디오 그래프
        pygame.draw.lines(screen, (200, 200, 200), False, list(zip(draw_audio_x, np.around(-audio_data*GRAPH_AUDIO_CY/2/peak+GRAPH_AUDIO_Y+GRAPH_AUDIO_CY/2).astype(np.int16))), 1)

        # 그래프 틀 
        screen.blit(text[1], (GRAPH_AUDIO_X, GRAPH_AUDIO_Y - 35))
        pygame.draw.rect(screen, (255, 255, 255), [GRAPH_AUDIO_X, GRAPH_AUDIO_Y, GRAPH_AUDIO_CX, GRAPH_AUDIO_CY], 2)

    # 상태바
    pygame.draw.rect(screen, (10, 10, 10), [0, 0, WIDTH, 30], 0)
    mouse_temp = win32api.GetCursorPos()
    if win_x + WIDTH - 120 <= mouse_temp[0] <= win_x + WIDTH - 80 and win_y + 0 <= mouse_temp[1] <= win_y + 30 :
        pygame.draw.rect(screen, (100, 100, 100), [WIDTH - 120, 0, 40, 30], 0)        
    if win_x + WIDTH - 80 <= mouse_temp[0] <= win_x + WIDTH - 40 and win_y + 0 <= mouse_temp[1] <= win_y + 30 :
        pygame.draw.rect(screen, (100, 100, 100), [WIDTH - 80, 0, 40, 30], 0)
    if win_x + WIDTH - 40 <= mouse_temp[0] <= win_x + WIDTH and win_y + 0 <= mouse_temp[1] <= win_y + 30 :
        pygame.draw.rect(screen, (255, 0, 0), [WIDTH - 40, 0, 40, 30], 0)
    
    if eventKey_capture:
        pygame.draw.polygon(screen, (255, 255, 255), [[WIDTH-102, 11], [WIDTH-96, 15], [WIDTH-102, 19]], 0) # play
        pygame.draw.aalines(screen, (255, 255, 255), True, [[WIDTH-103, 10], [WIDTH-95, 15], [WIDTH-103, 20]], True) # play
    else:
        pygame.draw.line(screen, (255, 255, 255), [WIDTH-103, 10], [WIDTH-103, 20], 3) # pause
        pygame.draw.line(screen, (255, 255, 255), [WIDTH-97, 10], [WIDTH-97, 20], 3) # pause
    pygame.draw.line(screen, (255, 255, 255), [WIDTH-65, 20], [WIDTH-55, 20], 1) # _
    pygame.draw.line(screen, (255, 255, 255), [WIDTH-25, 10], [WIDTH-15, 20], 1) # X
    pygame.draw.line(screen, (255, 255, 255), [WIDTH-25, 20], [WIDTH-15, 10], 1) # X
    screen.blit(text[0], (15, 5))

    # 프레임 완성    
    pygame.display.update()
