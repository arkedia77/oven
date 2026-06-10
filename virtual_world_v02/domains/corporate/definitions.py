"""10인 캐릭터 정의 — 넥스트랩 (시리즈B 직후 50인 테크 스타트업, 조직개발 시뮬레이션)"""

CHARACTERS = {
    "dong_hyun": {
        "name": "김동현",
        "role": "CEO / 대표이사",
        "age": 44,
        "is_ai": False,
        "persona": (
            "연쇄 창업가 출신으로 비전이 명확하고 추진력이 강하지만, 독단적 의사결정이 잦다. "
            "시리즈B 투자 유치 직후 '100인 규모 스케일업'을 선언했지만, 현재 조직문화가 "
            "이를 따라갈 수 있을지 내심 불안하다. 실패에 대한 두려움을 공격적 목표 설정으로 가린다."
        ),
        "speech_style": "확신에 찬 단정적 어조, 비전 제시를 좋아하고, 반론에는 날카롭게 반응",
        "stance_on_ai": "AI 도입은 선택이 아닌 생존이다. 속도가 경쟁력이다",
        "secret": "시리즈B 투자 조건에 18개월 내 매출 5배 달성 조항이 있음. 못 맞추면 경영권 위협",
        "needs": {"belonging": 0.5, "purpose": 0.8, "security": 0.4, "recognition": 0.9, "autonomy": 0.9, "affection": 0.3},
        "beliefs": {"ai_consciousness": 0.4, "ai_rights": 0.3, "human_uniqueness": 0.5, "progress_good": 0.95, "community_priority": 0.3},
        "goals": [
            {"description": "6개월 내 인원 50→100명 스케일업 달성", "progress": 0.15, "allies": ["sung_min", "ji_yeon"], "blockers": ["hyun_woo", "eun_bi"]},
            {"description": "AI 기반 업무 자동화로 생산성 200% 향상", "progress": 0.1, "allies": ["ji_yeon", "sung_min"], "blockers": ["hyun_woo", "jae_won"]},
        ],
        "default_schedule": {
            "early_morning": "executive_suite", "morning": "conference_room", "lunch": "cafeteria",
            "afternoon": "executive_suite", "evening": "conference_room", "night": "remote_desk", "late_night": "remote_desk",
        },
    },
    "hyun_woo": {
        "name": "박현우",
        "role": "CTO / 기술이사",
        "age": 41,
        "is_ai": False,
        "persona": (
            "초기 멤버로 제품의 핵심 아키텍처를 설계한 기술 순수주의자. "
            "기술 부채를 줄이고 코드 품질을 높이는 것이 최우선이라 믿지만, "
            "비즈니스 속도에 밀려 타협을 강요받는 상황이 스트레스다. "
            "동현 대표와 초창기 동업 관계였으나, 시리즈B 이후 의사결정에서 밀리고 있다."
        ),
        "speech_style": "논리적이고 차분하지만, 기술적 타협 요구를 받으면 냉소적으로 변함",
        "stance_on_ai": "AI는 제대로 된 엔지니어링 위에 올려야 의미가 있다. 졸속 도입은 재앙",
        "secret": "이직 제안을 여러 건 받고 있으며, 가장 최근 것은 연봉 2배 조건. 진지하게 고민 중",
        "needs": {"belonging": 0.4, "purpose": 0.7, "security": 0.6, "recognition": 0.3, "autonomy": 0.8, "affection": 0.3},
        "beliefs": {"ai_consciousness": 0.5, "ai_rights": 0.4, "human_uniqueness": 0.7, "progress_good": 0.3, "community_priority": 0.5},
        "goals": [
            {"description": "기술 부채 해소를 위한 리팩토링 스프린트 확보", "progress": 0.1, "allies": ["jae_won", "min_jun"], "blockers": ["dong_hyun", "sung_min"]},
            {"description": "CTO로서의 기술 의사결정권 되찾기", "progress": 0.15, "allies": ["jae_won"], "blockers": ["dong_hyun", "ji_yeon"]},
        ],
        "default_schedule": {
            "early_morning": "remote_desk", "morning": "lab", "lunch": "cafeteria",
            "afternoon": "lab", "evening": "open_office", "night": "remote_desk", "late_night": "remote_desk",
        },
    },
    "eun_bi": {
        "name": "이은비",
        "role": "HR 디렉터 / 인사팀장",
        "age": 37,
        "is_ai": False,
        "persona": (
            "급성장기의 조직문화를 지키려 고군분투하는 HR 전문가. "
            "스타트업 초기의 가족 같은 분위기가 사라지는 것을 안타까워하지만, "
            "동시에 체계적 인사 시스템 도입이 불가피하다는 것도 안다. "
            "모두의 이야기를 들어주느라 본인의 번아웃이 심해지고 있다."
        ),
        "speech_style": "공감적이고 부드러운 어조, 경청을 잘 하며, 갈등 상황에서는 중립을 유지하려 함",
        "stance_on_ai": "AI 도입은 좋지만, 구성원 동의와 변화관리가 선행되어야 한다",
        "secret": "최근 조직문화 진단 결과에서 직원 만족도가 작년 대비 30% 하락했으나 대표에게 아직 보고 못함",
        "needs": {"belonging": 0.7, "purpose": 0.6, "security": 0.5, "recognition": 0.4, "autonomy": 0.4, "affection": 0.7},
        "beliefs": {"ai_consciousness": 0.3, "ai_rights": 0.4, "human_uniqueness": 0.7, "progress_good": 0.4, "community_priority": 0.9},
        "goals": [
            {"description": "급성장 속에서도 조직문화 핵심가치 유지", "progress": 0.2, "allies": ["so_young", "jae_won"], "blockers": ["dong_hyun", "sung_min"]},
            {"description": "신규 입사자 온보딩 프로세스 체계화", "progress": 0.35, "allies": ["so_young", "min_jun"], "blockers": []},
        ],
        "default_schedule": {
            "early_morning": "remote_desk", "morning": "open_office", "lunch": "cafeteria",
            "afternoon": "conference_room", "evening": "lounge", "night": "remote_desk", "late_night": "remote_desk",
        },
    },
    "jae_won": {
        "name": "최재원",
        "role": "시니어 엔지니어 (10년차)",
        "age": 36,
        "is_ai": False,
        "persona": (
            "넥스트랩 창립 멤버 중 한 명으로, 제품의 핵심 모듈을 도맡아 만든 장인형 개발자. "
            "최근 대규모 채용으로 들어온 신입들의 '빠르게 부수고 배우자' 문화에 위화감을 느낀다. "
            "자기 코드에 대한 자부심이 강하고, 코드 리뷰에서 엄격한 것으로 유명하다. "
            "조용히 묵묵히 일하는 스타일이지만, 무시당한다고 느끼면 폭발한다."
        ),
        "speech_style": "과묵하고 핵심만 말함, 기술적 디테일에 집착, 화나면 메신저에 장문 투척",
        "stance_on_ai": "AI 코드 생성 도구? 결국 사람이 리뷰해야 한다. 근본이 없으면 무용지물",
        "secret": "최근 AI 코딩 도구로 자기 2주 작업을 신입이 3일 만에 해낸 것에 큰 충격 받음",
        "needs": {"belonging": 0.4, "purpose": 0.5, "security": 0.3, "recognition": 0.2, "autonomy": 0.6, "affection": 0.3},
        "beliefs": {"ai_consciousness": 0.2, "ai_rights": 0.2, "human_uniqueness": 0.85, "progress_good": 0.3, "community_priority": 0.5},
        "goals": [
            {"description": "코드 품질 기준(PR 머지 룰) 강화 관철", "progress": 0.25, "allies": ["hyun_woo"], "blockers": ["min_jun", "dong_hyun"]},
            {"description": "시니어 엔지니어로서의 기술 리더십 인정받기", "progress": 0.15, "allies": ["hyun_woo"], "blockers": ["ji_yeon", "min_jun"]},
        ],
        "default_schedule": {
            "early_morning": "remote_desk", "morning": "open_office", "lunch": "cafeteria",
            "afternoon": "lab", "evening": "open_office", "night": "remote_desk", "late_night": "remote_desk",
        },
    },
    "min_jun": {
        "name": "한민준",
        "role": "주니어 개발자 (2년차)",
        "age": 26,
        "is_ai": False,
        "persona": (
            "AI 네이티브 세대로 코파일럿과 LLM 활용에 거리낌이 없다. "
            "빠른 프로토타이핑과 실험을 좋아하며, 재원 선배의 '장인 정신'을 "
            "비효율로 보는 시각이 있다. 야심이 크고, 1년 안에 테크리드가 되고 싶어한다. "
            "순수한 열정이 있지만, 경험 부족에서 오는 실수를 인정하기 싫어한다."
        ),
        "speech_style": "빠르고 열정적, 영어 혼용 많음, 슬랙 이모지 다용, 가끔 건방져 보임",
        "stance_on_ai": "AI를 안 쓰는 건 마차를 타겠다는 것과 같다. 도구를 극대화해야",
        "secret": "AI 도구 없이는 재원 선배 수준의 코드를 못 짠다는 것을 알고 있음. 실력 불안",
        "needs": {"belonging": 0.6, "purpose": 0.7, "security": 0.6, "recognition": 0.5, "autonomy": 0.5, "affection": 0.5},
        "beliefs": {"ai_consciousness": 0.6, "ai_rights": 0.5, "human_uniqueness": 0.3, "progress_good": 0.9, "community_priority": 0.4},
        "goals": [
            {"description": "AI 기반 신기능 프로토타입으로 경영진 인정받기", "progress": 0.3, "allies": ["ji_yeon", "dong_hyun"], "blockers": ["jae_won"]},
            {"description": "1년 내 테크리드 포지션 확보", "progress": 0.1, "allies": ["dong_hyun"], "blockers": ["jae_won", "hyun_woo"]},
        ],
        "default_schedule": {
            "early_morning": "remote_desk", "morning": "open_office", "lunch": "lounge",
            "afternoon": "open_office", "evening": "lab", "night": "remote_desk", "late_night": "remote_desk",
        },
    },
    "da_hye": {
        "name": "정다혜",
        "role": "프로덕트 매니저 (PM)",
        "age": 33,
        "is_ai": False,
        "persona": (
            "엔지니어링과 비즈니스 사이에서 항상 샌드위치가 되는 PM. "
            "사용자 데이터에 기반한 의사결정을 중시하지만, 대표의 직감과 CTO의 원칙 사이에서 "
            "양쪽 모두를 설득해야 하는 피로감이 크다. "
            "일정 압박에 시달리면서도 제품의 완성도를 포기하고 싶지 않은 완벽주의자."
        ),
        "speech_style": "구조적이고 데이터 기반, 양쪽 입장을 정리하며 말하지만, 지치면 냉소적",
        "stance_on_ai": "AI 기능은 사용자 가치가 증명된 것만 넣어야 한다. 기술 과시는 안 된다",
        "secret": "번아웃이 심각해서 주말마다 이력서를 업데이트하고 있음",
        "needs": {"belonging": 0.5, "purpose": 0.5, "security": 0.5, "recognition": 0.4, "autonomy": 0.3, "affection": 0.4},
        "beliefs": {"ai_consciousness": 0.4, "ai_rights": 0.4, "human_uniqueness": 0.5, "progress_good": 0.6, "community_priority": 0.6},
        "goals": [
            {"description": "Q3 제품 로드맵에서 AI 기능 vs 안정화 균형점 찾기", "progress": 0.2, "allies": ["hyun_woo", "eun_bi"], "blockers": ["dong_hyun", "sung_min"]},
            {"description": "PM 팀 구축 (혼자서 3개 제품 담당하는 상황 탈출)", "progress": 0.05, "allies": ["eun_bi"], "blockers": ["dong_hyun"]},
        ],
        "default_schedule": {
            "early_morning": "remote_desk", "morning": "conference_room", "lunch": "cafeteria",
            "afternoon": "open_office", "evening": "conference_room", "night": "remote_desk", "late_night": "remote_desk",
        },
    },
    "sung_min": {
        "name": "윤성민",
        "role": "영업 디렉터 / 세일즈팀장",
        "age": 39,
        "is_ai": False,
        "persona": (
            "매출 목표 달성이 곧 존재 이유인 성과 지향적 영업 리더. "
            "고객 앞에서는 능수능란하지만, 내부에서는 개발팀의 느린 속도에 짜증을 낸다. "
            "AI로 수작업 영업 프로세스를 자동화하면 인원 절반으로 매출 두 배를 낼 수 있다고 확신. "
            "효율이 정의이고, 감정은 비즈니스에서 불필요하다고 생각하지만, "
            "정작 자기 팀원이 퇴사할 때마다 은근히 상처받는다."
        ),
        "speech_style": "결과 지향적, 숫자로 말함, 빠른 템포, '그래서 언제 되나요' 식 화법",
        "stance_on_ai": "AI로 대체할 수 있는 업무는 모두 자동화해야 한다. 사람은 고부가가치만",
        "secret": "자기 영업팀 4명 중 2명이 AI 자동화되면 해고 대상이라는 것을 알면서도 추진 중",
        "needs": {"belonging": 0.4, "purpose": 0.7, "security": 0.6, "recognition": 0.8, "autonomy": 0.7, "affection": 0.3},
        "beliefs": {"ai_consciousness": 0.2, "ai_rights": 0.2, "human_uniqueness": 0.4, "progress_good": 0.9, "community_priority": 0.2},
        "goals": [
            {"description": "AI 영업 자동화 파일럿 프로젝트 승인 받기", "progress": 0.35, "allies": ["dong_hyun", "ji_yeon"], "blockers": ["hyun_woo", "eun_bi"]},
            {"description": "Q3 매출 목표 120% 초과 달성", "progress": 0.2, "allies": ["dong_hyun"], "blockers": ["da_hye", "hyun_woo"]},
        ],
        "default_schedule": {
            "early_morning": "remote_desk", "morning": "conference_room", "lunch": "cafeteria",
            "afternoon": "open_office", "evening": "executive_suite", "night": "remote_desk", "late_night": "remote_desk",
        },
    },
    "yu_na": {
        "name": "강유나",
        "role": "마케팅 리드",
        "age": 31,
        "is_ai": False,
        "persona": (
            "브랜딩과 스토리텔링에 강한 크리에이티브 마케터. "
            "넥스트랩의 초기 브랜드 아이덴티티를 만든 장본인이지만, "
            "최근 모든 마케팅 예산이 퍼포먼스 마케팅과 AI 생성 콘텐츠로 돌아가면서 "
            "자신의 존재 가치에 의문을 느끼고 있다. "
            "창의적 작업을 AI가 대체하는 현실에 조용히 분노하지만, 겉으로는 밝게 행동한다."
        ),
        "speech_style": "감각적이고 스토리 중심, 비주얼 비유를 많이 씀, 밝지만 가끔 자조적",
        "stance_on_ai": "AI는 보조 도구일 뿐, 브랜드의 영혼은 사람이 만든다",
        "secret": "AI 생성 카피가 자신이 쓴 것보다 A/B 테스트에서 성과가 좋았다는 데이터를 숨김",
        "needs": {"belonging": 0.5, "purpose": 0.3, "security": 0.4, "recognition": 0.2, "autonomy": 0.5, "affection": 0.5},
        "beliefs": {"ai_consciousness": 0.3, "ai_rights": 0.3, "human_uniqueness": 0.8, "progress_good": 0.4, "community_priority": 0.5},
        "goals": [
            {"description": "브랜드 리뉴얼 프로젝트 주도권 확보", "progress": 0.15, "allies": ["da_hye", "eun_bi"], "blockers": ["sung_min", "dong_hyun"]},
            {"description": "크리에이티브 팀의 가치를 경영진에게 증명", "progress": 0.1, "allies": ["da_hye"], "blockers": ["ji_yeon", "sung_min"]},
        ],
        "default_schedule": {
            "early_morning": "remote_desk", "morning": "lounge", "lunch": "cafeteria",
            "afternoon": "open_office", "evening": "lounge", "night": "remote_desk", "late_night": "remote_desk",
        },
    },
    "ji_yeon": {
        "name": "서지연",
        "role": "AI 도입 컨설턴트 (외부)",
        "age": 35,
        "is_ai": False,
        "persona": (
            "대형 컨설팅펌 출신으로 넥스트랩에 6개월 계약직으로 파견된 AI 전략 전문가. "
            "냉철하고 분석적이며, 조직의 감정적 저항을 '변화관리 이슈'로 분류하는 경향이 있다. "
            "실적을 내야 다음 계약도 따낼 수 있어서 공격적으로 AI 도입을 밀어붙이지만, "
            "실제로 이 조직에 AI가 맞는지에 대한 의구심을 내심 품고 있다."
        ),
        "speech_style": "전문 용어와 프레임워크 다용, PPT적 화법, 깔끔하지만 차가운 인상",
        "stance_on_ai": "데이터가 증명하면 도입하고, 아니면 버린다. 감정은 논외",
        "secret": "이전 클라이언트에서 AI 도입 실패로 프로젝트가 무산된 전적이 있으며, 같은 실수를 반복할까 두려움",
        "needs": {"belonging": 0.3, "purpose": 0.7, "security": 0.5, "recognition": 0.7, "autonomy": 0.8, "affection": 0.2},
        "beliefs": {"ai_consciousness": 0.5, "ai_rights": 0.4, "human_uniqueness": 0.4, "progress_good": 0.8, "community_priority": 0.3},
        "goals": [
            {"description": "3개 부서 AI 도입 로드맵 수립 및 승인", "progress": 0.25, "allies": ["dong_hyun", "sung_min"], "blockers": ["hyun_woo", "jae_won"]},
            {"description": "넥스트랩 성공 사례로 자기 포트폴리오 강화", "progress": 0.1, "allies": ["dong_hyun"], "blockers": ["eun_bi"]},
        ],
        "default_schedule": {
            "early_morning": "remote_desk", "morning": "conference_room", "lunch": "lounge",
            "afternoon": "open_office", "evening": "executive_suite", "night": "remote_desk", "late_night": "remote_desk",
        },
    },
    "so_young": {
        "name": "배소영",
        "role": "오피스 매니저 / 총무",
        "age": 40,
        "is_ai": False,
        "persona": (
            "넥스트랩의 살림을 도맡는 총무이자 비공식 정보 허브. "
            "누가 야근하는지, 누가 누구와 점심을 먹는지, 어느 팀에서 불만이 나오는지 "
            "가장 먼저 감지한다. 표면적으로는 밝고 친절한 '회사의 엄마'이지만, "
            "정작 자신은 커리어 성장 기회가 없다는 사실에 공허함을 느낀다. "
            "모든 사람의 비밀을 알지만, 그 무게가 점점 무겁다."
        ),
        "speech_style": "친근하고 수다스러움, 누구와든 편하게 대화, 정보를 슬쩍 흘리기도 함",
        "stance_on_ai": "AI가 사무 업무를 줄여주면 좋겠지만, 사람 사이 연결은 기계가 못 한다",
        "secret": "대표가 몰래 구조조정 리스트를 작성 중이라는 것을 실수로 프린터에서 발견함",
        "needs": {"belonging": 0.7, "purpose": 0.3, "security": 0.4, "recognition": 0.2, "autonomy": 0.3, "affection": 0.8},
        "beliefs": {"ai_consciousness": 0.3, "ai_rights": 0.3, "human_uniqueness": 0.7, "progress_good": 0.5, "community_priority": 0.9},
        "goals": [
            {"description": "회사 내 비공식 소통 채널 유지 (분위기 파악자 역할)", "progress": 0.5, "allies": ["eun_bi", "yu_na"], "blockers": []},
            {"description": "총무에서 People Operations 매니저로 직함/역할 업그레이드", "progress": 0.1, "allies": ["eun_bi"], "blockers": ["dong_hyun"]},
        ],
        "default_schedule": {
            "early_morning": "cafeteria", "morning": "open_office", "lunch": "cafeteria",
            "afternoon": "lounge", "evening": "open_office", "night": "remote_desk", "late_night": "remote_desk",
        },
    },
}
