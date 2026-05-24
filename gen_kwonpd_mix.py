"""Generate 권PD mix LoKR songs."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

from acestep.handler import AceStepHandler
from acestep.inference import GenerationParams, GenerationConfig, generate_music

BEST_CKPT = r"C:\Users\leo\kwonpd_mix_output\checkpoints\epoch_200_loss_0.9599"
SAVE_DIR = r"C:\Users\leo\kwonpd_mix_samples"

SONGS = [
    {
        "name": "01_그리운_사람아",
        "caption": "Korean trot, emotional female vocals, vibrato, slow ballad, string orchestra, piano, melancholic, 70 BPM",
        "lyrics": """[verse]
창밖에 비가 내리면
그대 생각이 나요
함께 걷던 그 골목길
빗소리에 잠기네요

[chorus]
그리운 사람아
어디에 있나요
이 마음 전할 수 없어
오늘도 혼자 울어요

[verse]
사진 속 웃던 얼굴
손끝으로 쓸어보며
돌아오지 못할 시간
가슴에 묻어둡니다"""
    },
    {
        "name": "02_인생한잔",
        "caption": "Korean trot, warm male vocals, medium tempo, accordion, folk guitar, cheerful, nostalgic, 92 BPM",
        "lyrics": """[verse]
인생이란 술잔에다
기쁨 한 모금 따르고
슬픔 한 방울 섞어서
오늘도 한잔 하세

[chorus]
자 한잔 하소 인생을
울고 웃는 게 사는 거지
넘어져도 다시 일어나
그게 바로 우리 인생

[verse]
젊은 날의 실수에도
돌아보면 웃음이지
주름살이 늘어가도
마음만은 청춘이야"""
    },
    {
        "name": "03_떠나가는_배",
        "caption": "Korean trot, powerful male vocals, dramatic vibrato, brass, electric guitar, energetic, 110 BPM",
        "lyrics": """[verse]
부산항 부두가에
갈매기 날아오르고
뱃고동 울려퍼지면
가슴이 먹먹하오

[chorus]
떠나가는 배야
내 사랑 싣고 가느냐
파도야 잠잠해라
그이를 돌려보내라

[verse]
수평선 저 너머로
점점 작아지는 그대
손수건 흔들다가
주저앉아 울었소"""
    },
    {
        "name": "04_봄이오면",
        "caption": "Korean trot, bright female vocals, upbeat, synthesizer, light percussion, spring mood, hopeful, 120 BPM",
        "lyrics": """[verse]
꽃잎이 흩날리는
삼월의 어느 날에
새로운 사랑이
내게로 찾아왔네

[chorus]
봄이 오면 봄이 오면
마음도 꽃이 피네
겨울밤 얼었던 심장이
사르르 녹아내려요

[verse]
벚꽃길 나란히 걸으며
수줍게 눈 맞추고
살며시 잡은 손끝에
봄바람이 스쳐가네"""
    },
    {
        "name": "05_고향역",
        "caption": "Korean trot, emotional male vocals, deep vibrato, acoustic guitar, harmonica, sentimental ballad, 76 BPM",
        "lyrics": """[verse]
간이역 벤치 위에
가방 하나 내려놓고
십 년 만에 돌아온
고향의 하늘을 봐

[chorus]
달라진 건 나뿐이고
이 마을은 그대로네
어머니 기다리던
그 대문은 열려 있소

[verse]
논두렁 밭두렁 사이로
뛰어놀던 그 시절
소꿉친구 얼굴이
아른아른 떠오르오"""
    },
]

handler = AceStepHandler()
handler.initialize_service(
    project_root=r"C:\Users\leo\ace-step-v15",
    config_path=None,
    device="cuda",
    offload_to_cpu=False,
)

print(f"Loading LoKR: {BEST_CKPT}", flush=True)
handler.load_lora(BEST_CKPT)

for i, song in enumerate(SONGS):
    print(f"\n[{i+1}/{len(SONGS)}] {song['name']}", flush=True)
    save_path = os.path.join(SAVE_DIR, song["name"])
    os.makedirs(save_path, exist_ok=True)
    params = GenerationParams(
        caption=song["caption"],
        lyrics=song["lyrics"],
        instrumental=False,
        vocal_language="ko",
        duration=60,
        task_type="text2music",
        thinking=False,
    )
    config = GenerationConfig(
        batch_size=1,
        seeds=[42],
        audio_format="wav",
    )
    res = generate_music(
        dit_handler=handler,
        llm_handler=None,
        params=params,
        config=config,
        save_dir=save_path,
    )
    for audio in res.audios:
        print(f"  -> {audio.get('path','saved')}", flush=True)

print("\nALL DONE!", flush=True)
