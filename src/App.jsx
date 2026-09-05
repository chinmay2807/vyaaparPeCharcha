import React, { useState, useEffect, useRef } from "react";
import {
  Mic,
  MicOff,
  Camera,
  CheckCircle2,
  AlertCircle,
  Clock,
  TrendingUp,
  Receipt,
  Package,
  Volume2,
  Check,
  Sparkles,
  Home,
  User,
  ShoppingBag,
  Phone,
  Store,
  ShieldCheck,
  Languages,
  LogOut,
  CreditCard,
  ChevronRight
} from "lucide-react";

const TRANSLATIONS = {
  en: {
    appTitle: "Vyapaar",
    appSubtitle: "Charcha",
    tagline: "ORAL COMMERCE ERP",
    storeActive: "Active Merchant Account",
    storeName: "Ramesh Kirana & General Store",
    storeDesc: "Voice-driven retail ledger. Recording orders & udhaar in real time.",
    speakNow: "Record Order",
    tapToRecord: "Tap orb to record order for Ramesh Store",
    pendingCredit: "Ramesh Total Due",
    ordersToday: "Orders in Queue",
    activeOrdersDesc: "4 Active Parties",
    creditDesc: "Pending across ledgers",
    voiceOrder: "Voice Order",
    scanBill: "Scan Bill",
    khataLedger: "Khata Ledger",
    recentOrders: "Ramesh Store Recent Records",
    viewAll: "View All Ledgers",
    dueBalance: "due balance",
    voiceFirstTitle: "AI Voice Recognition",
    listening: "Listening... Dictate items, quantities, and party name",
    tapToSpeak: "Tap orb to speak or pause",
    pipelineTitle: "SARVAM AI PIPELINE",
    analyzing: "Analyzing Speech",
    verified: "Added to Ramesh Ledger",
    sttLabel: "Saaras Speech-to-Text Transcription",
    sttSample: "Ramesh ko kal ke liye 6 peti Sprite, 4 Coke, aur 20 Limca bhejna. Uska last 12,500 pending hai.",
    llmLabel: "Indic LLM Entity Extraction",
    llmSample: "Party: Ramesh Store • 6 peti Sprite, 4 Coke, 20 Limca • Pending: ₹12,500",
    clarificationTitle: "Clarification for Ramesh Store:",
    clarificationPrompt: "Did Ramesh request 20 bottles or 20 crates of Limca?",
    bottles: "20 Bottles",
    crates: "20 Crates",
    ledgerSuccess: "Ramesh Store Ledger Updated",
    listenBtn: "Play Voice Confirmation",
    replayBtn: "Replay",
    ordersMgmt: "Party Order Management",
    allOrdersDesc: "Ramesh, Iqbal, Gupta & Kavita ledger orders",
    scanTitle: "Ramesh Store Invoice Scanner",
    scanDesc: "Scan handwritten supplier slips & kacha bills directly into Ramesh's ledger balance.",
    captureBtn: "Reconcile Ramesh Bill",
    retailType: "Retail Kirana & Daily FMCG",
    voiceLang: "Merchant Language",
    indicModel: "Sarvam Indic AI Model",
    paymentQr: "Ramesh Store UPI",
    switchMerchant: "Switch Active Account",
    ttsConfirmation: "Ramesh store ka order likh liya gaya hai: Chhe peti Sprite, chaar Coke, aur bees Limca. Baarah hazaar paanch sau rupaye pending baki hain.",
    navHome: "Home",
    navOrders: "Orders",
    navSpeak: "Voice Pulse",
    navLedger: "Ledger",
    navProfile: "Ramesh"
  },
  hinglish: {
    appTitle: "Vyapaar",
    appSubtitle: "Charcha",
    tagline: "VOICE-FIRST BUSINESS ERP",
    storeActive: "Chalu Vyapaari Khata",
    storeName: "Ramesh Kirana & General Store",
    storeDesc: "Bolkar naye orders likhein aur Ramesh ka udhaar hisab dekhein.",
    speakNow: "Order Bolein",
    tapToRecord: "Ramesh ke order ke liye orb tap karein",
    pendingCredit: "Ramesh Ka Baki",
    ordersToday: "Aaj Ke Orders",
    activeOrdersDesc: "4 Vyapaari Khate",
    creditDesc: "Baki udhaar hisaab",
    voiceOrder: "Bolkar Order",
    scanBill: "Parchi Scan",
    khataLedger: "Khata Bahi",
    recentOrders: "Ramesh Store Ke Orders",
    viewAll: "Sabhi Dekhein",
    dueBalance: "baki rashi",
    voiceFirstTitle: "AI Awaaz Recognition",
    listening: "Sun rahe hain... Ramesh ka order bolein",
    tapToSpeak: "Bolne ke liye orb tap karein",
    pipelineTitle: "SARVAM AI PIPELINE",
    analyzing: "Jaanch Chal Rahi",
    verified: "Ramesh Khate Mein Jud Gaya",
    sttLabel: "Saaras Speech-to-Text Transcription",
    sttSample: "Ramesh ko kal ke liye 6 peti Sprite, 4 Coke, aur 20 Limca bhejna. Uska last 12,500 pending hai.",
    llmLabel: "Indic LLM Entity Extraction",
    llmSample: "Party: Ramesh Store • 6 peti Sprite, 4 Coke, 20 Limca • Baki: ₹12,500",
    clarificationTitle: "Ramesh Ke Order Ki Pushti:",
    clarificationPrompt: "20 Limca ki bottles chahiye ya 20 crates?",
    bottles: "20 Bottles",
    crates: "20 Crates",
    ledgerSuccess: "Ramesh Ka Khata Update Ho Gaya",
    listenBtn: "Audio Suno",
    replayBtn: "Dobara Suno",
    ordersMgmt: "Orders Prabandhan",
    allOrdersDesc: "Ramesh, Iqbal, Gupta aur Kavita ke orders",
    scanTitle: "Kacha Bill & Parchi Scanner",
    scanDesc: "Ramesh ke bill aur supplier ki parchi seedhe bahi-khate mein jodein.",
    captureBtn: "Parchi Scan Aur Milao",
    retailType: "Kirana & Wholesale Store",
    voiceLang: "Bolne Ki Bhasha",
    indicModel: "Sarvam Indic Engine",
    paymentQr: "Ramesh UPI QR",
    switchMerchant: "Khata Badlein",
    ttsConfirmation: "Ramesh store ka order likh liya gaya hai: Chhe peti Sprite, chaar Coke, aur bees Limca. Baarah hazaar paanch sau rupaye pending baki hain.",
    navHome: "Home",
    navOrders: "Orders",
    navSpeak: "Voice Pulse",
    navLedger: "Khata",
    navProfile: "Ramesh"
  },
  hi: {
    appTitle: "व्यापार",
    appSubtitle: "चर्चा",
    tagline: "आवाज़ आधारित व्यापार ERP",
    storeActive: "सक्रिय व्यापारी खाता",
    storeName: "रमेश किराना एवं जनरल स्टोर",
    storeDesc: "बोलकर रमेश का खाता और बकाया उधार तुरंत दर्ज करें।",
    speakNow: "ऑर्डर बोलें",
    tapToRecord: "रमेश के ऑर्डर के लिए ओर्ब दबाएं",
    pendingCredit: "रमेश कुल बकाया",
    ordersToday: "आज के ऑर्डर",
    activeOrdersDesc: "४ सक्रिय व्यापारी",
    creditDesc: "कुल बाकी उधार",
    voiceOrder: "बोलकर ऑर्डर",
    scanBill: "पर्ची स्कैन",
    khataLedger: "खाता बही",
    recentOrders: "रमेश स्टोर के हालिया ऑर्डर",
    viewAll: "सभी देखें",
    dueBalance: "बाकी राशि",
    voiceFirstTitle: "एआई आवाज़ पहचान",
    listening: "सुन रहे हैं... रमेश का ऑर्डर और सामान बोलें",
    tapToSpeak: "बोलने के लिए ओर्ब दबाएं",
    pipelineTitle: "सर्वम एआई इंजन",
    analyzing: "विश्लेषण जारी",
    verified: "रमेश के खाते में दर्ज",
    sttLabel: "सारस स्पीच-टू-टेक्स्ट ट्रांसक्रिप्शन",
    sttSample: "रमेश को कल के लिए ६ पेटी स्प्राइट, ४ कोक, और २० लिम्का भेजना। उसका पिछला १२,५०० पेंडिंग है।",
    llmLabel: "इंडिक एलएलएम एंटिटी एक्सट्रैक्शन",
    llmSample: "पार्टी: रमेश स्टोर • ६ पेटी स्प्राइट, ४ कोक, २० लिम्का • बकाया: ₹१२,५००",
    clarificationTitle: "रमेश स्टोर के लिए स्पष्टीकरण:",
    clarificationPrompt: "२० लिम्का की बोतलें चाहिए या २० क्रेट?",
    bottles: "२० बोतलें",
    crates: "२० क्रेट",
    ledgerSuccess: "रमेश स्टोर खाता बही अपडेट हुई",
    listenBtn: "पुष्टि सुनें",
    replayBtn: "पुनः सुनें",
    ordersMgmt: "पार्टी ऑर्डर प्रबंधन",
    allOrdersDesc: "रमेश, इक़बाल, गुप्ता एवं कविता के ऑर्डर",
    scanTitle: "कच्चा बिल और पर्ची स्कैनर",
    scanDesc: "आपूर्तिकर्ता की पर्ची सीधे रमेश के बही-खाते में दर्ज करें।",
    captureBtn: "पर्ची स्कैन करें",
    retailType: "किराना एवं दैनिक उत्पाद",
    voiceLang: "चुनी गई भाषा",
    indicModel: "सर्वम इंडिक मॉडल",
    paymentQr: "रमेश स्टोर यूपीआई",
    switchMerchant: "व्यापारी बदलें",
    ttsConfirmation: "रमेश स्टोर का ऑर्डर दर्ज कर लिया गया है: छः पेटी स्प्राइट, चार कोक, और बीस लिम्का। बारह हज़ार पाँच सौ रुपये बकाया हैं।",
    navHome: "होम",
    navOrders: "ऑर्डर्स",
    navSpeak: "वॉइस पल्स",
    navLedger: "खाता",
    navProfile: "रमेश"
  },
  ta: {
    appTitle: "வியாபார்",
    appSubtitle: "சர்ச்சை",
    tagline: "குரல் வழி வணிக ERP",
    storeActive: "செயலில் உள்ள கணக்கு",
    storeName: "ரமேஷ் மளிகை & பொது அங்காடி",
    storeDesc: "ரமேஷ் கடையின் ஆர்டர்கள் மற்றும் உதார் கணக்குகளைப் பதிவு செய்யவும்.",
    speakNow: "ஆர்டர் பேசவும்",
    tapToRecord: "ரமேஷ் ஆர்டரைப் பதிவு செய்ய",
    pendingCredit: "ரமேஷ் மொத்த பாக்கி",
    ordersToday: "இன்றைய ஆர்டர்கள்",
    activeOrdersDesc: "4 வாடிக்கையாளர்கள்",
    creditDesc: "மொத்த நிலுவை உதார்",
    voiceOrder: "குரல் ஆர்டர்",
    scanBill: "ரசீது ஸ்கேன்",
    khataLedger: "கணக்கு புத்தகம்",
    recentOrders: "ரமேஷ் கடையின் ஆர்டர்கள்",
    viewAll: "அனைத்தும்",
    dueBalance: "நிலுவை தொகை",
    voiceFirstTitle: "AI குரல் அறிதல்",
    listening: "கேட்கிறது... ரமேஷ் கடைக்கான ஆர்டரைச் சொல்லவும்",
    tapToSpeak: "பேச உருண்டையைத் தொடவும்",
    pipelineTitle: "சார்வம் AI பகுப்பாய்வு",
    analyzing: "பகுப்பாய்வு நடக்கிறது",
    verified: "ரமேஷ் கணக்கில் சேர்க்கப்பட்டது",
    sttLabel: "சாரஸ் பேச்சு-எழுத்து மாற்றம் (STT)",
    sttSample: "ரமேஷ் கடைக்கு நாளைக்கு 6 பெட்டி ஸ்ப்ரைட், 4 கோக், 20 லிம்கா அனுப்பவும். பழைய பாக்கி 12,500 நிலுவையில் உள்ளது.",
    llmLabel: "இண்டிக் LLM தரவு பிரித்தெடுத்தல்",
    llmSample: "வாடிக்கையாளர்: ரமேஷ் ஸ்டோர் • 6 பெட்டி ஸ்ப்ரைட், 4 கோக், 20 லிம்கா • பாக்கி: ₹12,500",
    clarificationTitle: "ரமேஷ் கடைக்கான விளக்கம்:",
    clarificationPrompt: "20 லிம்கா பாட்டில்களா அல்லது 20 பெட்டிகளா (crates)?",
    bottles: "20 பாட்டில்கள்",
    crates: "20 பெட்டிகள்",
    ledgerSuccess: "ரமேஷ் கணக்கு புத்தகம் புதுப்பிக்கப்பட்டது",
    listenBtn: "ஆடியோ கேட்க",
    replayBtn: "மீண்டும் கேட்க",
    ordersMgmt: "ஆர்டர்கள் மேலாண்மை",
    allOrdersDesc: "ரமேஷ், இக்பால், குப்தா மற்றும் கவிதா ஆர்டர்கள்",
    scanTitle: "ரமேஷ் பில் & ரசீது ஸ்கேனர்",
    scanDesc: "கையால் எழுதப்பட்ட ரசீதுகளை நேரடியாக ரமேஷ் கணக்கில் சேர்க்கலாம்.",
    captureBtn: "ரசீதைச் சரிபார்க்கவும்",
    retailType: "மளிகை & நுகர்பொருள் சில்லறை வணிகம்",
    voiceLang: "பேச்சு மொழி",
    indicModel: "சார்வம் இண்டிக் AI",
    paymentQr: "ரமேஷ் ஸ்டோர் UPI",
    switchMerchant: "கடையை மாற்றவும்",
    ttsConfirmation: "ரமேஷ் கடைக்கான ஆர்டர் பதிவு செய்யப்பட்டது: 6 பெட்டி ஸ்ப்ரைட், 4 கோக் மற்றும் 20 லிம்கா. முந்தைய பாக்கி பன்னிரண்டாயிரத்து ஐந்நூறு ரூபாய் நிலுவையில் உள்ளது.",
    navHome: "முகப்பு",
    navOrders: "ஆர்டர்கள்",
    navSpeak: "வாய்ஸ் பல்ஸ்",
    navLedger: "கணக்கு",
    navProfile: "ரமேஷ்"
  }
};

const INITIAL_ORDERS = [
  {
    id: "ORD-041",
    customer: "Ramesh Store",
    phone: "+91 98765 43210",
    items: [
      { name: "Sprite", qty: "6 peti" },
      { name: "Coke", qty: "4 Coke" },
      { name: "Limca", qty: "20 bottles" }
    ],
    delivery: "Kal (Tomorrow)",
    totalAmount: 18400,
    pendingDue: 12500,
    status: "Confirmed",
    timestamp: "Just now",
    source: "Voice STT"
  },
  {
    id: "ORD-040",
    customer: "Iqbal General Store",
    phone: "+91 98450 12345",
    items: [
      { name: "Atta 10kg", qty: "5 bags" },
      { name: "Mustard Oil 1L", qty: "12 pouches" }
    ],
    delivery: "Today",
    totalAmount: 4900,
    pendingDue: 3240,
    status: "Dispatched",
    timestamp: "2 hrs ago",
    source: "Voice Note"
  },
  {
    id: "ORD-039",
    customer: "Gupta Wholesaler",
    phone: "+91 97123 45678",
    items: [{ name: "Basmati Rice 25kg", qty: "2 bags" }],
    delivery: "Pending",
    totalAmount: 11200,
    pendingDue: 8900,
    status: "Pending",
    timestamp: "Yesterday",
    source: "Supplier Bill Scan"
  },
  {
    id: "ORD-038",
    customer: "Kavita Supermart",
    phone: "+91 99001 88223",
    items: [
      { name: "Surf Excel 1kg", qty: "10 packs" },
      { name: "Vim Bar", qty: "2 cartons" }
    ],
    delivery: "Completed",
    totalAmount: 3450,
    pendingDue: 1875,
    status: "Delivered",
    timestamp: "2 days ago",
    source: "Voice Note"
  }
];

export default function VyapaarApp() {
  const [lang, setLang] = useState("en");
  const [activeTab, setActiveTab] = useState("record");
  const [isRecording, setIsRecording] = useState(false);
  const [recordTimer, setRecordTimer] = useState(0);
  const [audioLevel, setAudioLevel] = useState(1);
  const [processingStep, setProcessingStep] = useState(null);
  const [orders, setOrders] = useState(INITIAL_ORDERS);
  const [audioPlayed, setAudioPlayed] = useState(false);
  const [clarificationNeeded, setClarificationNeeded] = useState(false);
  const [orderFilter, setOrderFilter] = useState("all");

  const timerRef = useRef(null);
  const t = TRANSLATIONS[lang];

  useEffect(() => {
    if (!isRecording) {
      setAudioLevel(1);
      return;
    }
    const interval = setInterval(() => {
      setAudioLevel(1 + Math.random() * 0.08);
    }, 150);
    return () => clearInterval(interval);
  }, [isRecording]);

  const toggleRecording = () => {
    if (isRecording) {
      clearInterval(timerRef.current);
      setIsRecording(false);
      simulateSarvamProcessing();
    } else {
      setIsRecording(true);
      setRecordTimer(0);
      setProcessingStep(null);
      setAudioPlayed(false);
      timerRef.current = setInterval(() => {
        setRecordTimer((prev) => prev + 1);
      }, 1000);
    }
  };

  const simulateSarvamProcessing = () => {
    setProcessingStep("stt");
    setTimeout(() => {
      setProcessingStep("llm");
      setTimeout(() => {
        setProcessingStep("clarify");
        setClarificationNeeded(true);
      }, 1300);
    }, 1500);
  };

  const resolveClarification = (choice) => {
    setProcessingStep("tts");
    setTimeout(() => {
      setProcessingStep("done");
      setClarificationNeeded(false);

      const newEntry = {
        id: `ORD-0${orders.length + 42}`,
        customer: "Ramesh Store",
        phone: "+91 98765 43210",
        items: [
          { name: "Sprite", qty: "6 peti" },
          { name: "Coke", qty: "4 Coke" },
          { name: "Limca", qty: choice === "crates" ? "20 crates" : "20 bottles" }
        ],
        delivery: "Kal (Tomorrow)",
        totalAmount: 18400,
        pendingDue: 12500,
        status: "Confirmed",
        timestamp: "Just now",
        source: "Voice STT"
      };
      setOrders([newEntry, ...orders]);
    }, 1200);
  };

  const playTTSFeedback = () => {
    setAudioPlayed(true);
    if ("speechSynthesis" in window) {
      const msg = new SpeechSynthesisUtterance(t.ttsConfirmation);
      if (lang === "ta") {
        msg.lang = "ta-IN";
      } else if (lang === "hi" || lang === "hinglish") {
        msg.lang = "hi-IN";
      } else {
        msg.lang = "en-IN";
      }
      window.speechSynthesis.speak(msg);
    }
  };

  const filteredOrders = orders.filter((o) => {
    if (orderFilter === "all") return true;
    return o.status.toLowerCase() === orderFilter.toLowerCase();
  });

  return (
    <div className="flex justify-center min-h-screen bg-[#F0F7FF] text-[#0B192C] font-sans antialiased selection:bg-[#2563EB] selection:text-white">
      {/* Phone container in pure monochromatic blue tones */}
      <div className="w-full max-w-md bg-gradient-to-b from-[#FFFFFF] via-[#F0F7FF] to-[#E2EFFF] border-x border-[#BFDBFE] flex flex-col min-h-screen shadow-2xl relative pb-24 overflow-hidden">
        
        {/* Ambient Blue Backing Glows */}
        <div className="absolute top-[-5%] left-[-15%] w-[340px] h-[340px] bg-gradient-to-br from-[#3B82F6]/20 to-[#60A5FA]/25 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-[20%] right-[-20%] w-[300px] h-[300px] bg-gradient-to-tr from-[#1D4ED8]/20 to-[#93C5FD]/20 rounded-full blur-3xl pointer-events-none" />

        {/* Top Header */}
        <header className="px-5 py-3.5 border-b border-[#BFDBFE] bg-white/85 backdrop-blur-md sticky top-0 z-20 flex justify-between items-center shadow-xs">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-[#1D4ED8] via-[#2563EB] to-[#60A5FA] p-0.5 shadow-xs flex items-center justify-center flex-shrink-0">
              <div className="w-full h-full bg-white rounded-full flex items-center justify-center">
                <Sparkles className="w-3.5 h-3.5 text-[#2563EB]" />
              </div>
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-tight text-[#0B192C] flex items-center gap-1">
                {t.appTitle} <span className="text-[#2563EB]">{t.appSubtitle}</span>
              </h1>
              <p className="text-[9px] text-[#2563EB] font-semibold tracking-wider uppercase">
                {t.tagline}
              </p>
            </div>
          </div>

          {/* Language Switcher */}
          <div className="flex items-center gap-1">
            <div className="flex items-center bg-[#DBEAFE] border border-[#BFDBFE] rounded-full p-0.5 text-[10.5px] font-semibold">
              <button
                onClick={() => setLang("en")}
                className={`px-2 py-0.5 rounded-full transition ${
                  lang === "en" ? "bg-[#2563EB] text-white shadow-xs" : "text-[#1E3E62] hover:text-[#2563EB]"
                }`}
              >
                EN
              </button>
              <button
                onClick={() => setLang("hinglish")}
                className={`px-1.5 py-0.5 rounded-full transition ${
                  lang === "hinglish" ? "bg-[#2563EB] text-white shadow-xs" : "text-[#1E3E62] hover:text-[#2563EB]"
                }`}
              >
                Hinglish
              </button>
              <button
                onClick={() => setLang("hi")}
                className={`px-1.5 py-0.5 rounded-full transition ${
                  lang === "hi" ? "bg-[#2563EB] text-white shadow-xs" : "text-[#1E3E62] hover:text-[#2563EB]"
                }`}
              >
                हिंदी
              </button>
              <button
                onClick={() => setLang("ta")}
                className={`px-1.5 py-0.5 rounded-full transition ${
                  lang === "ta" ? "bg-[#2563EB] text-white shadow-xs" : "text-[#1E3E62] hover:text-[#2563EB]"
                }`}
              >
                தமிழ்
              </button>
            </div>

            <button 
              onClick={() => setActiveTab("profile")}
              className="w-7 h-7 rounded-full bg-gradient-to-tr from-[#1D4ED8] to-[#3B82F6] text-white font-bold text-xs flex items-center justify-center shadow-xs ml-1 flex-shrink-0"
            >
              RS
            </button>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 px-5 py-4 space-y-4 relative z-10 overflow-y-auto">
          
          {/* ================= HOME VIEW ================= */}
          {activeTab === "home" && (
            <div className="space-y-4">
              {/* Profile Card */}
              <div className="rounded-[28px] p-6 bg-white border border-[#BFDBFE] shadow-sm flex flex-col space-y-4">
                <div>
                  <span className="text-[10px] tracking-wide uppercase font-bold text-[#2563EB] bg-[#DBEAFE] border border-[#BFDBFE] px-3 py-1 rounded-full inline-block">
                    {t.storeActive}
                  </span>
                </div>

                <div className="space-y-1">
                  <h2 className="text-lg font-bold text-[#0B192C] tracking-tight leading-snug">
                    {t.storeName}
                  </h2>
                  <p className="text-xs text-[#3B5270] leading-relaxed">
                    {t.storeDesc}
                  </p>
                </div>

                <div className="pt-3 border-t border-[#DBEAFE] flex flex-wrap items-center justify-between gap-3">
                  <span className="text-xs font-medium text-[#3B5270]">
                    {t.tapToRecord}
                  </span>
                  <button
                    onClick={() => setActiveTab("record")}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-gradient-to-r from-[#1D4ED8] to-[#3B82F6] text-white font-semibold text-xs shadow-md shadow-[#2563EB]/25 hover:opacity-95 active:scale-95 transition"
                  >
                    <Mic className="w-3.5 h-3.5" />
                    {t.speakNow}
                  </button>
                </div>
              </div>

              {/* Stats Overview */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-white p-4 rounded-2xl border border-[#BFDBFE] shadow-xs">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-[10px] text-[#2563EB] uppercase font-bold tracking-wider">{t.pendingCredit}</span>
                    <TrendingUp className="w-4 h-4 text-[#2563EB]" />
                  </div>
                  <p className="text-lg font-bold text-[#0B192C]">₹12,500</p>
                  <p className="text-[10px] text-[#476082] mt-0.5">{t.creditDesc}</p>
                </div>

                <div className="bg-white p-4 rounded-2xl border border-[#BFDBFE] shadow-xs">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-[10px] text-[#3B82F6] uppercase font-bold tracking-wider">{t.ordersToday}</span>
                    <Package className="w-4 h-4 text-[#3B82F6]" />
                  </div>
                  <p className="text-lg font-bold text-[#0B192C]">{t.activeOrdersDesc}</p>
                  <p className="text-[10px] text-[#476082] mt-0.5">₹18,400 active</p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-3 gap-2.5">
                <button
                  onClick={() => setActiveTab("record")}
                  className="p-3 bg-white border border-[#BFDBFE] rounded-2xl flex flex-col items-center justify-center gap-1.5 hover:bg-[#F0F7FF] shadow-xs active:scale-95 transition"
                >
                  <div className="w-9 h-9 rounded-xl bg-[#DBEAFE] flex items-center justify-center text-[#2563EB]">
                    <Mic className="w-4 h-4" />
                  </div>
                  <span className="text-[10.5px] font-semibold text-[#0B192C]">{t.voiceOrder}</span>
                </button>

                <button
                  onClick={() => setActiveTab("scan")}
                  className="p-3 bg-white border border-[#BFDBFE] rounded-2xl flex flex-col items-center justify-center gap-1.5 hover:bg-[#F0F7FF] shadow-xs active:scale-95 transition"
                >
                  <div className="w-9 h-9 rounded-xl bg-[#EFF6FF] flex items-center justify-center text-[#3B82F6]">
                    <Camera className="w-4 h-4" />
                  </div>
                  <span className="text-[10.5px] font-semibold text-[#0B192C]">{t.scanBill}</span>
                </button>

                <button
                  onClick={() => setActiveTab("ledger")}
                  className="p-3 bg-white border border-[#BFDBFE] rounded-2xl flex flex-col items-center justify-center gap-1.5 hover:bg-[#F0F7FF] shadow-xs active:scale-95 transition"
                >
                  <div className="w-9 h-9 rounded-xl bg-[#DBEAFE] flex items-center justify-center text-[#1D4ED8]">
                    <Receipt className="w-4 h-4" />
                  </div>
                  <span className="text-[10.5px] font-semibold text-[#0B192C]">{t.khataLedger}</span>
                </button>
              </div>

              {/* Recent Orders */}
              <div className="space-y-2.5 pt-1">
                <div className="flex justify-between items-center px-1">
                  <h3 className="text-xs uppercase tracking-wider text-[#2563EB] font-bold">
                    {t.recentOrders}
                  </h3>
                  <button
                    onClick={() => setActiveTab("orders")}
                    className="text-[11px] text-[#2563EB] font-semibold flex items-center gap-0.5 hover:underline"
                  >
                    {t.viewAll} ({orders.length}) <ChevronRight className="w-3 h-3" />
                  </button>
                </div>

                {orders.slice(0, 2).map((item) => (
                  <div
                    key={item.id}
                    className="p-4 bg-white border border-[#BFDBFE] rounded-2xl flex items-center justify-between shadow-xs"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-[#0B192C]">{item.customer}</span>
                        <span className="text-[9px] font-mono text-[#2563EB] bg-[#DBEAFE] border border-[#BFDBFE] px-1.5 py-0.2 rounded-full font-semibold">
                          {item.id}
                        </span>
                      </div>
                      <p className="text-[11px] text-[#3B5270] mt-1">
                        {item.items.map((it) => `${it.qty} ${it.name}`).join(", ")}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs font-mono font-bold text-[#2563EB]">
                        ₹{item.pendingDue.toLocaleString("en-IN")}
                      </p>
                      <span className="text-[9px] text-[#3B82F6] font-semibold">{item.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ================= VOICE 3D IRIDESCENT ORB SCREEN ================= */}
          {activeTab === "record" && (
            <div className="space-y-4">
              <div className="rounded-[32px] p-6 border border-[#BFDBFE] bg-white shadow-sm flex flex-col items-center justify-center text-center overflow-hidden">
                
                <div className="flex items-center space-x-2 bg-[#EFF6FF] border border-[#BFDBFE] px-3.5 py-1.5 rounded-full shadow-xs mb-3">
                  <div className="w-3 h-3 rounded-full bg-gradient-to-tr from-[#1D4ED8] via-[#3B82F6] to-[#93C5FD]" />
                  <span className="text-xs font-semibold text-[#0B192C]">Voice Pulse • Ramesh Order</span>
                </div>

                <h2 className="text-base font-bold tracking-tight text-[#0B192C] mb-4">
                  {t.voiceFirstTitle}
                </h2>

                {/* ========================================================
                    3D IRIDESCENT BLUE ORB (WITH CENTERED MICROPHONE)
                   ======================================================== */}
                <div
                  className="relative flex items-center justify-center transition-transform duration-200 my-5"
                  style={{ transform: `scale(${audioLevel})` }}
                >
                  {/* Surrounding Atmospheric Blue Aura */}
                  <div className="absolute w-64 h-64 rounded-full bg-gradient-to-tr from-[#1D4ED8]/30 via-[#3B82F6]/35 to-[#93C5FD]/45 blur-3xl pointer-events-none" />

                  {/* Solid 3D Iridescent Sphere */}
                  <div
                    onClick={toggleRecording}
                    className="relative w-52 h-52 rounded-full overflow-hidden border-2 border-[#93C5FD] cursor-pointer active:scale-95 transition-all duration-300 flex items-center justify-center"
                    style={{
                      boxShadow: `
                        0 24px 60px rgba(29, 78, 216, 0.4),
                        0 10px 25px rgba(59, 130, 246, 0.35),
                        inset 0 0 25px rgba(255, 255, 255, 0.8),
                        inset 0 -18px 36px rgba(11, 25, 44, 0.6),
                        inset 0 16px 32px rgba(147, 197, 253, 0.6)
                      `,
                      background: `
                        radial-gradient(circle at 45% 30%, #E0F2FE 0%, #93C5FD 18%, #3B82F6 45%, #1D4ED8 70%, #0B192C 100%)
                      `
                    }}
                  >
                    {/* Metallic Iridescent Sheen Bands */}
                    <div className="absolute inset-0 bg-gradient-to-tr from-[#2563EB]/40 via-transparent to-[#60A5FA]/50 mix-blend-overlay opacity-90 pointer-events-none" />

                    {/* Caustic Curvature Highlight */}
                    <div
                      className="absolute top-2 left-5 right-5 h-20 rounded-[50%] bg-gradient-to-b from-white/90 via-white/30 to-transparent pointer-events-none transform -rotate-12 blur-[0.6px]"
                      style={{ clipPath: "ellipse(48% 35% at 50% 30%)" }}
                    />

                    {/* Secondary Bottom Blue Rim Reflection */}
                    <div className="absolute bottom-2 left-7 right-7 h-8 rounded-full bg-gradient-to-t from-white/75 via-[#93C5FD]/60 to-transparent blur-[0.7px] pointer-events-none" />

                    {/* Direct Specular Catchlight */}
                    <div className="absolute top-6 left-9 w-3 h-2 rounded-full bg-white blur-[0.3px] transform -rotate-45 pointer-events-none" />

                    {/* Centered Microphone Inside Orb */}
                    <div className="relative z-10 w-16 h-16 rounded-full bg-white/20 backdrop-blur-sm border border-white/50 flex items-center justify-center shadow-lg transition-transform duration-200 hover:scale-105">
                      {isRecording ? (
                        <MicOff className="w-8 h-8 text-white drop-shadow-[0_2px_8px_rgba(0,0,0,0.4)] animate-pulse" />
                      ) : (
                        <Mic className="w-8 h-8 text-white drop-shadow-[0_2px_8px_rgba(0,0,0,0.4)]" />
                      )}
                    </div>
                  </div>

                  {/* Active Recording Ripple Rings */}
                  {isRecording && (
                    <div className="absolute w-[220px] h-[220px] rounded-full border-2 border-[#3B82F6] pointer-events-none opacity-50 animate-ping" />
                  )}
                </div>

                <div className="mt-2 flex items-center space-x-2 bg-[#EFF6FF] border border-[#BFDBFE] px-3.5 py-1.5 rounded-full shadow-xs">
                  <span className={`w-2 h-2 rounded-full ${isRecording ? "bg-[#2563EB] animate-ping" : "bg-[#3B82F6]"}`} />
                  <span className="text-xs font-medium text-[#1E3E62]">
                    {isRecording ? t.listening : t.tapToSpeak}
                  </span>
                </div>
              </div>

              {/* Processing Pipeline Stages */}
              {processingStep && (
                <div className="bg-white border border-[#BFDBFE] rounded-3xl p-5 space-y-3.5 shadow-sm">
                  <div className="flex items-center justify-between text-xs font-bold text-[#0B192C] border-b border-[#DBEAFE] pb-2">
                    <span className="flex items-center gap-1.5 text-[#2563EB]">
                      <Sparkles className="w-3.5 h-3.5" />
                      {t.pipelineTitle}
                    </span>
                    <span className="text-[10px] font-mono uppercase text-[#1D4ED8] bg-[#DBEAFE] px-2 py-0.5 rounded-full border border-[#BFDBFE] font-bold">
                      {processingStep === "done" ? t.verified : t.analyzing}
                    </span>
                  </div>

                  <div className="flex items-start space-x-3">
                    <div className="mt-0.5">
                      {processingStep === "stt" ? (
                        <div className="w-4 h-4 border-2 border-[#2563EB] border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <CheckCircle2 className="w-4 h-4 text-[#2563EB]" />
                      )}
                    </div>
                    <div className="flex-1">
                      <p className="text-xs font-bold text-[#0B192C]">
                        {t.sttLabel}
                      </p>
                      <p className="text-[11px] text-[#3B5270] italic mt-0.5">
                        "{t.sttSample}"
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start space-x-3">
                    <div className="mt-0.5">
                      {processingStep === "llm" ? (
                        <div className="w-4 h-4 border-2 border-[#2563EB] border-t-transparent rounded-full animate-spin" />
                      ) : processingStep === "stt" ? (
                        <div className="w-4 h-4 rounded-full border border-[#BFDBFE]" />
                      ) : (
                        <CheckCircle2 className="w-4 h-4 text-[#2563EB]" />
                      )}
                    </div>
                    <div className="flex-1">
                      <p className="text-xs font-bold text-[#0B192C]">
                        {t.llmLabel}
                      </p>
                      <p className="text-[11px] text-[#2563EB] font-mono font-medium mt-0.5">
                        {t.llmSample}
                      </p>
                    </div>
                  </div>

                  {clarificationNeeded && (
                    <div className="bg-[#EFF6FF] border border-[#BFDBFE] rounded-2xl p-4 my-2 space-y-2.5 shadow-xs">
                      <div className="flex items-center space-x-2 text-[#2563EB] text-xs font-bold">
                        <AlertCircle className="w-4 h-4 flex-shrink-0" />
                        <span>{t.clarificationTitle}</span>
                      </div>
                      <p className="text-xs text-[#0B192C]">
                        {t.clarificationPrompt}
                      </p>
                      <div className="flex gap-2 pt-1">
                        <button
                          onClick={() => resolveClarification("bottles")}
                          className="flex-1 py-2 px-3 bg-[#2563EB] hover:bg-[#1D4ED8] text-white rounded-xl text-xs font-bold transition shadow-xs"
                        >
                          {t.bottles}
                        </button>
                        <button
                          onClick={() => resolveClarification("crates")}
                          className="flex-1 py-2 px-3 bg-white hover:bg-slate-50 text-[#2563EB] border border-[#BFDBFE] rounded-xl text-xs font-bold transition shadow-xs"
                        >
                          {t.crates}
                        </button>
                      </div>
                    </div>
                  )}

                  {processingStep === "done" && (
                    <div className="pt-2.5 border-t border-[#DBEAFE] flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Check className="w-4 h-4 text-[#2563EB]" />
                        <span className="text-xs text-[#0B192C] font-bold">
                          {t.ledgerSuccess}
                        </span>
                      </div>
                      <button
                        onClick={playTTSFeedback}
                        className="flex items-center space-x-1.5 text-xs bg-[#DBEAFE] hover:bg-[#BFDBFE] text-[#1D4ED8] font-bold px-3 py-1.5 rounded-full border border-[#BFDBFE] transition"
                      >
                        <Volume2 className="w-3.5 h-3.5" />
                        <span>{audioPlayed ? t.replayBtn : t.listenBtn}</span>
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ================= ORDERS VIEW ================= */}
          {activeTab === "orders" && (
            <div className="space-y-3.5">
              <div className="flex justify-between items-center px-1">
                <div>
                  <h2 className="text-base font-bold text-[#0B192C]">
                    {t.ordersMgmt}
                  </h2>
                  <p className="text-[10px] text-[#3B5270] font-medium">{t.allOrdersDesc}</p>
                </div>
                <span className="text-xs font-mono text-[#2563EB] bg-[#DBEAFE] px-2.5 py-0.5 rounded-full border border-[#BFDBFE] font-bold">
                  {filteredOrders.length} Orders
                </span>
              </div>

              {/* Filter Pills */}
              <div className="flex gap-1.5 overflow-x-auto pb-1 text-[11px]">
                {["all", "confirmed", "dispatched", "pending", "delivered"].map((status) => (
                  <button
                    key={status}
                    onClick={() => setOrderFilter(status)}
                    className={`capitalize px-3 py-1 rounded-full border transition font-medium ${
                      orderFilter === status
                        ? "bg-[#2563EB] text-white border-[#2563EB] shadow-xs"
                        : "bg-white text-[#0B192C] border-[#BFDBFE] hover:border-[#2563EB]"
                    }`}
                  >
                    {status}
                  </button>
                ))}
              </div>

              {/* Orders List */}
              <div className="space-y-2.5">
                {filteredOrders.map((order) => (
                  <div
                    key={order.id}
                    className="p-4 bg-white border border-[#BFDBFE] rounded-2xl space-y-2 shadow-xs"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-sm font-bold text-[#0B192C]">
                            {order.customer}
                          </h4>
                          <span className="text-[9px] font-mono text-[#2563EB] bg-[#DBEAFE] px-2 py-0.2 rounded-full border border-[#BFDBFE] font-bold">
                            {order.id}
                          </span>
                        </div>
                        <p className="text-[10px] text-[#3B5270] flex items-center gap-1 mt-0.5">
                          <Phone className="w-2.5 h-2.5 text-[#3B82F6]" /> {order.phone}
                        </p>
                      </div>
                      <span className="text-[10px] font-bold text-[#1D4ED8] bg-[#DBEAFE] px-2.5 py-0.5 rounded-full border border-[#BFDBFE]">
                        {order.status}
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-1 py-1">
                      {order.items.map((it, idx) => (
                        <span
                          key={idx}
                          className="bg-[#EFF6FF] text-[#0B192C] border border-[#BFDBFE] px-2.5 py-0.5 rounded-lg text-[10px] font-mono font-medium"
                        >
                          {it.qty} {it.name}
                        </span>
                      ))}
                    </div>

                    <div className="pt-2 border-t border-[#DBEAFE] flex justify-between items-center text-[10px] text-[#3B5270]">
                      <span>Source: {order.source}</span>
                      <span className="font-mono text-[#0B192C] font-bold">
                        Total: ₹{order.totalAmount.toLocaleString("en-IN")}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ================= LEDGER VIEW ================= */}
          {activeTab === "ledger" && (
            <div className="space-y-3">
              <div className="flex items-center justify-between px-1">
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-[#2563EB]">
                    {t.khataLedger}
                  </h3>
                  <p className="text-[10px] text-[#3B5270] font-medium">{t.creditDesc}</p>
                </div>
                <span className="text-[11px] text-[#1D4ED8] font-mono font-bold">
                  {orders.length} Records
                </span>
              </div>

              <div className="space-y-2.5">
                {orders.map((item) => (
                  <div
                    key={item.id}
                    className="p-4 bg-white border border-[#BFDBFE] rounded-2xl shadow-xs hover:border-[#2563EB]/40 transition"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center space-x-2">
                          <h4 className="text-sm font-bold text-[#0B192C]">
                            {item.customer}
                          </h4>
                          <span className="text-[9px] font-mono text-[#2563EB] bg-[#DBEAFE] border border-[#BFDBFE] px-2 py-0.2 rounded-full font-bold">
                            {item.id}
                          </span>
                        </div>
                        <div className="text-[11px] text-[#3B5270] mt-1.5 space-x-1 flex flex-wrap">
                          {item.items.map((it, idx) => (
                            <span
                              key={idx}
                              className="bg-[#EFF6FF] text-[#0B192C] border border-[#BFDBFE] px-2 py-0.5 rounded-lg text-[10px] mr-1 mb-1 font-mono"
                            >
                              {it.qty} {it.name}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-xs font-mono font-bold text-[#2563EB]">
                          ₹{item.pendingDue.toLocaleString("en-IN")}
                        </p>
                        <p className="text-[10px] text-[#3B5270]">{t.dueBalance}</p>
                      </div>
                    </div>

                    <div className="mt-3 pt-2.5 border-t border-[#DBEAFE] flex items-center justify-between text-[10px] text-[#3B5270]">
                      <span className="flex items-center">
                        <Clock className="w-3 h-3 mr-1 text-[#3B82F6]" />
                        Delivery: {item.delivery}
                      </span>
                      <span className="text-[#2563EB] font-bold">
                        {item.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ================= SCAN BILL VIEW ================= */}
          {activeTab === "scan" && (
            <div className="space-y-4 text-center py-8">
              <div className="w-20 h-20 bg-gradient-to-tr from-[#DBEAFE] to-[#EFF6FF] border-2 border-dashed border-[#2563EB] rounded-3xl flex items-center justify-center mx-auto text-[#2563EB] shadow-xs">
                <Camera className="w-9 h-9" />
              </div>
              <div className="px-4">
                <h3 className="text-base font-bold text-[#0B192C]">
                  {t.scanTitle}
                </h3>
                <p className="text-xs text-[#3B5270] max-w-xs mx-auto mt-1.5">
                  {t.scanDesc}
                </p>
              </div>

              <div className="pt-2 px-6">
                <button
                  onClick={() => setActiveTab("ledger")}
                  className="w-full py-3 px-4 bg-gradient-to-r from-[#1D4ED8] to-[#3B82F6] text-white rounded-2xl text-xs font-bold transition shadow-md shadow-[#2563EB]/25 flex items-center justify-center gap-2"
                >
                  <Camera className="w-4 h-4" />
                  {t.captureBtn}
                </button>
              </div>
            </div>
          )}

          {/* ================= PROFILE VIEW ================= */}
          {activeTab === "profile" && (
            <div className="space-y-4">
              <div className="p-5 rounded-3xl border border-[#BFDBFE] bg-white flex items-center gap-4 shadow-xs">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-[#1D4ED8] to-[#3B82F6] text-white font-bold text-xl flex items-center justify-center shadow-md">
                  RS
                </div>
                <div>
                  <h3 className="text-base font-bold text-[#0B192C]">
                    {t.storeName}
                  </h3>
                  <p className="text-xs text-[#2563EB] font-bold flex items-center gap-1">
                    <Store className="w-3 h-3" /> {t.retailType}
                  </p>
                  <p className="text-[10px] text-[#3B5270] mt-0.5">GSTIN: 27AABCR1234F1Z9</p>
                </div>
              </div>

              <div className="bg-white border border-[#BFDBFE] rounded-3xl divide-y divide-[#DBEAFE] shadow-xs">
                <div className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-xl bg-[#DBEAFE] flex items-center justify-center text-[#2563EB]">
                      <Languages className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-[#0B192C]">{t.voiceLang}</p>
                      <p className="text-[10px] text-[#3B5270] capitalize">
                        {lang === "en" ? "English" : lang === "hinglish" ? "Hinglish" : lang === "hi" ? "हिंदी (Hindi)" : "தமிழ் (Tamil)"}
                      </p>
                    </div>
                  </div>
                  <span className="text-[10px] text-[#1D4ED8] font-bold bg-[#DBEAFE] px-2 py-0.5 rounded-full border border-[#BFDBFE]">
                    Active
                  </span>
                </div>

                <div className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-xl bg-[#DBEAFE] flex items-center justify-center text-[#2563EB]">
                      <ShieldCheck className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-[#0B192C]">{t.indicModel}</p>
                      <p className="text-[10px] text-[#3B5270]">Saaras STT & Bulbul TTS</p>
                    </div>
                  </div>
                  <span className="text-[10px] text-[#2563EB] font-mono font-bold">v2.4</span>
                </div>

                <div className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-xl bg-[#DBEAFE] flex items-center justify-center text-[#3B82F6]">
                      <CreditCard className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-[#0B192C]">{t.paymentQr}</p>
                      <p className="text-[10px] text-[#3B5270]">rameshstore@upi</p>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-[#93C5FD]" />
                </div>
              </div>

              <div className="p-4 bg-white border border-[#BFDBFE] rounded-2xl text-[11px] text-[#3B5270] space-y-1">
                <p className="text-[#2563EB] font-bold">Team Binary Brains</p>
                <p>Chinmay Agarwal • Jayesh Motwani • Pushpmitra • Krishnave</p>
              </div>

              <button 
                onClick={() => setActiveTab("home")}
                className="w-full py-2.5 border border-[#BFDBFE] bg-[#DBEAFE]/40 rounded-2xl text-xs font-bold text-[#1D4ED8] hover:bg-[#DBEAFE] flex items-center justify-center gap-1.5 transition"
              >
                <LogOut className="w-3.5 h-3.5" /> {t.switchMerchant}
              </button>
            </div>
          )}
        </main>

        {/* Bottom Navigation Bar */}
        <nav className="absolute bottom-0 left-0 right-0 h-16 bg-white/95 border-t border-[#BFDBFE] backdrop-blur-xl px-4 flex justify-around items-center z-30 shadow-lg">
          <button
            onClick={() => setActiveTab("home")}
            className={`flex flex-col items-center justify-center space-y-1 transition ${
              activeTab === "home" ? "text-[#2563EB] font-bold" : "text-[#3B5270] hover:text-[#0B192C]"
            }`}
          >
            <Home className="w-4 h-4" />
            <span className="text-[9px]">{t.navHome}</span>
          </button>

          <button
            onClick={() => setActiveTab("orders")}
            className={`flex flex-col items-center justify-center space-y-1 transition ${
              activeTab === "orders" ? "text-[#2563EB] font-bold" : "text-[#3B5270] hover:text-[#0B192C]"
            }`}
          >
            <ShoppingBag className="w-4 h-4" />
            <span className="text-[9px]">{t.navOrders}</span>
          </button>

          {/* Centered Voice Orb Trigger */}
          <button
            onClick={() => setActiveTab("record")}
            className="flex flex-col items-center justify-center -mt-5"
          >
            <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-[#1D4ED8] via-[#2563EB] to-[#60A5FA] p-0.5 shadow-md shadow-[#2563EB]/40">
              <div className="w-full h-full bg-[#1D4ED8] hover:bg-[#2563EB] rounded-full flex items-center justify-center transition">
                <Mic className="w-5 h-5 text-white" />
              </div>
            </div>
            <span className="text-[9px] font-bold text-[#2563EB] mt-1">{t.navSpeak}</span>
          </button>

          <button
            onClick={() => setActiveTab("ledger")}
            className={`flex flex-col items-center justify-center space-y-1 transition ${
              activeTab === "ledger" ? "text-[#2563EB] font-bold" : "text-[#3B5270] hover:text-[#0B192C]"
            }`}
          >
            <Receipt className="w-4 h-4" />
            <span className="text-[9px]">{t.navLedger}</span>
          </button>

          <button
            onClick={() => setActiveTab("profile")}
            className={`flex flex-col items-center justify-center space-y-1 transition ${
              activeTab === "profile" ? "text-[#2563EB] font-bold" : "text-[#3B5270] hover:text-[#0B192C]"
            }`}
          >
            <User className="w-4 h-4" />
            <span className="text-[9px]">{t.navProfile}</span>
          </button>
        </nav>
      </div>
    </div>
  );
}