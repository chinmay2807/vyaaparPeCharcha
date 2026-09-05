import React, { useState, useRef } from "react";
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

// Multi-language dictionary with English, Hinglish, Hindi, and Tamil
const TRANSLATIONS = {
  en: {
    appTitle: "Vyapaar",
    appSubtitle: "Charcha",
    tagline: "ORAL COMMERCE ERP",
    storeActive: "Store Active • Counter 01",
    storeName: "Rajesh Provisions",
    storeDesc: "Ready to capture voice orders or reconcile supplier slips.",
    speakNow: "Speak Order",
    tapToRecord: "Tap to record order",
    pendingCredit: "Pending Credit",
    ordersToday: "Orders Today",
    activeOrdersDesc: "12 Active",
    creditDesc: "Across 4 merchants",
    voiceOrder: "Voice Order",
    scanBill: "Scan Bill",
    khataLedger: "Khata Ledger",
    recentOrders: "Recent Spoken Orders",
    viewAll: "View All",
    dueBalance: "due balance",
    voiceFirstTitle: "Speak your order naturally",
    voiceFirstDesc: "No forms or typing. State client, items, quantities, and credit dues.",
    listening: "Listening... Speak items, quantities, and customer name",
    readyMic: "Ready to capture speech",
    pipelineTitle: "COGNITIVE REASONING PIPELINE",
    analyzing: "Analyzing",
    verified: "Verified",
    sttLabel: "Speech-to-Text Transcription",
    sttSample: "Send 6 crates of Sprite, 4 Coke, and 20 Limca to Ramesh Store for tomorrow. His previous balance of 12,500 is still pending.",
    llmLabel: "Structured Entity Extraction",
    llmSample: "Party: Ramesh Store • 6 Sprite, 4 Coke, 20 Limca • Due: ₹12,500",
    clarificationTitle: "Clarification Required:",
    clarificationPrompt: "Did you mean 20 bottles or 20 crates of Limca?",
    bottles: "20 Bottles",
    crates: "20 Crates",
    ledgerSuccess: "Ledger Updated Successfully",
    listenBtn: "Listen Confirmation",
    replayBtn: "Replay",
    ordersMgmt: "Orders Management",
    allOrdersDesc: "All captured & dispatched inventory",
    scanTitle: "Physical Bill & Invoice Scanner",
    scanDesc: "Vision OCR analyzes handwritten slips and printed bills directly into structured ledger line items.",
    captureBtn: "Capture & Reconcile",
    retailType: "Retail Kirana & FMCG",
    voiceLang: "Spoken Language",
    indicModel: "Sarvam Indic AI Model",
    paymentQr: "Payment QR / UPI",
    switchMerchant: "Switch Merchant",
    ttsConfirmation: "Order recorded for Ramesh Store: 6 crates of Sprite, 4 Coke, and 20 Limca. Previous balance of 12,500 rupees remains pending.",
    navHome: "Home",
    navOrders: "Orders",
    navSpeak: "Speak",
    navLedger: "Ledger",
    navProfile: "Profile"
  },
  hinglish: {
    appTitle: "Vyapaar",
    appSubtitle: "Charcha",
    tagline: "VOICE-FIRST BUSINESS ERP",
    storeActive: "Dukan Chalu • Counter 01",
    storeName: "Rajesh Provisions",
    storeDesc: "Bolkar naye orders likhein ya kacha bill scan karein.",
    speakNow: "Bolkar Likhein",
    tapToRecord: "Order bolne ke liye tap karein",
    pendingCredit: "Baki Udhaar",
    ordersToday: "Aaj Ke Orders",
    activeOrdersDesc: "12 Chalu Hai",
    creditDesc: "4 Vyapaariyon Ka Baki",
    voiceOrder: "Bolkar Order",
    scanBill: "Parchi Scan",
    khataLedger: "Khata Bahi",
    recentOrders: "Haal Hi Ke Bolkar Likhe Orders",
    viewAll: "Sabhi Dekhein",
    dueBalance: "baki rashi",
    voiceFirstTitle: "Apni aam bhasha mein bolein",
    voiceFirstDesc: "Bina form bhare client, saaman, peti aur baki udhaar seedha darj karein.",
    listening: "Sun rahe hain... Saaman, quantity aur dukan ka naam bolein",
    readyMic: "Awaaz sunne ke liye taiyaar",
    pipelineTitle: "SARVAM AI REASONING PIPELINE",
    analyzing: "Jaanch Chal Rahi",
    verified: "Darj Ho Gaya",
    sttLabel: "Saaras Speech-to-Text Transcription",
    sttSample: "Ramesh ko kal ke liye 6 peti Sprite, 4 Coke, aur 20 Limca bhejna. Uska last 12,500 pending hai.",
    llmLabel: "Indic LLM Entity Extraction",
    llmSample: "Party: Ramesh Store • 6 Sprite, 4 Coke, 20 Limca • Baki: ₹12,500",
    clarificationTitle: "Jankari Ki Pushti Chahiye:",
    clarificationPrompt: "20 Limca ki bottles chahiye ya 20 crates?",
    bottles: "20 Bottles",
    crates: "20 Crates",
    ledgerSuccess: "Khata Safalta Se Update Ho Gaya",
    listenBtn: "Audio Suno",
    replayBtn: "Dobara Suno",
    ordersMgmt: "Orders Prabandhan",
    allOrdersDesc: "Sabhi darj aur bheje gaye orders",
    scanTitle: "Kacha Bill Aur Parchi Scanner",
    scanDesc: "Vision OCR se hath se likhi parchi aur supplier ke bill seedhe bahi-khate mein jud jaate hain.",
    captureBtn: "Photo Kheecho Aur Milao",
    retailType: "Kirana Aur FMCG Wholesale",
    voiceLang: "Bolne Ki Bhasha",
    indicModel: "Sarvam Indic Engine",
    paymentQr: "UPI Aur QR Code",
    switchMerchant: "Dukan Badlein",
    ttsConfirmation: "Ramesh store ka order likh liya gaya hai: Chhe peti Sprite, chaar Coke, aur bees Limca. Baarah hazaar paanch sau rupaye baki hain.",
    navHome: "Home",
    navOrders: "Orders",
    navSpeak: "Bolein",
    navLedger: "Khata",
    navProfile: "Profile"
  },
  hi: {
    appTitle: "व्यापार",
    appSubtitle: "चर्चा",
    tagline: "आवाज़ आधारित व्यापार ERP",
    storeActive: "दुकान चालू • काउंटर ०१",
    storeName: "राजेश प्रोविजन्स",
    storeDesc: "बोलकर नए ऑर्डर लिखें या आपूर्तिकर्ता की पर्चियां स्कैन करें।",
    speakNow: "बोलकर दर्ज करें",
    tapToRecord: "ऑर्डर बोलने के लिए दबाएं",
    pendingCredit: "कुल बाकी उधार",
    ordersToday: "आज के ऑर्डर",
    activeOrdersDesc: "१२ सक्रिय",
    creditDesc: "४ व्यापारियों से बाकी",
    voiceOrder: "बोलकर ऑर्डर",
    scanBill: "पर्ची स्कैन",
    khataLedger: "खाता बही",
    recentOrders: "हाल ही में बोले गए ऑर्डर",
    viewAll: "सभी देखें",
    dueBalance: "बाकी राशि",
    voiceFirstTitle: "स्वाभाविक रूप से बोलें",
    voiceFirstDesc: "बिना किसी फॉर्म के ग्राहक, सामान, मात्रा और बकाया राशि सीधे दर्ज करें।",
    listening: "सुन रहे हैं... सामान, मात्रा और ग्राहक का नाम बोलें",
    readyMic: "आवाज़ सुनने के लिए तैयार",
    pipelineTitle: "सर्वम एआई प्रोसेसिंग इंजन",
    analyzing: "विश्लेषण जारी",
    verified: "सत्यापित",
    sttLabel: "सारस स्पीच-टू-टेक्स्ट ट्रांसक्रिप्शन",
    sttSample: "रमेश को कल के लिए ६ पेटी स्प्राइट, ४ कोक, और २० लिम्का भेजना। उसका पिछला १२,५०० पेंडिंग है।",
    llmLabel: "इंडिक एलएलएम एंटिटी एक्सट्रैक्शन",
    llmSample: "पार्टी: रमेश स्टोर • ६ स्प्राइट, ४ कोक, २० लिम्का • बकाया: ₹१२,५००",
    clarificationTitle: "स्पष्टीकरण की आवश्यकता:",
    clarificationPrompt: "२० लिम्का की बोतलें चाहिए या २० क्रेट?",
    bottles: "२० बोतलें",
    crates: "२० क्रेट",
    ledgerSuccess: "खाता बही सफलतापूर्वक अपडेट हुई",
    listenBtn: "पुष्टि सुनें",
    replayBtn: "पुनः सुनें",
    ordersMgmt: "ऑर्डर प्रबंधन",
    allOrdersDesc: "सभी दर्ज और भेजे गए उत्पाद",
    scanTitle: "कच्चा बिल और पर्ची स्कैनर",
    scanDesc: "विज़न ओसीआर हाथ से लिखी पर्चियों और बिलों को सीधे खाता बही में दर्ज करता है।",
    captureBtn: "फोटो लें और मिलान करें",
    retailType: "किराना एवं थोक व्यापार",
    voiceLang: "चुनी गई भाषा",
    indicModel: "सर्वम इंडिक मॉडल",
    paymentQr: "भुगतान क्यूआर / यूपीआई",
    switchMerchant: "व्यापारी बदलें",
    ttsConfirmation: "रमेश स्टोर का ऑर्डर दर्ज कर लिया गया है: छः पेटी स्प्राइट, चार कोक, और बीस लिम्का। बारह हज़ार पाँच सौ रुपये बकाया हैं।",
    navHome: "होम",
    navOrders: "ऑर्डर्स",
    navSpeak: "बोलें",
    navLedger: "खाता",
    navProfile: "प्रोफ़ाइल"
  },
  ta: {
    appTitle: "வியாபார்",
    appSubtitle: "சர்ச்சை",
    tagline: "குரல் வழி வணிக ERP",
    storeActive: "கடை திறந்துள்ளது • கவுண்டர் 01",
    storeName: "ராஜேஷ் ப்ரொவிஷன்ஸ்",
    storeDesc: "குரல் மூலம் ஆர்டர்களைப் பதிவு செய்யவும் அல்லது பில்களை ஸ்கேன் செய்யவும்.",
    speakNow: "ஆர்டர் பேசவும்",
    tapToRecord: "ஆர்டரைப் பதிவு செய்ய தட்டவும்",
    pendingCredit: "நிலுவை கடன் (உதார்)",
    ordersToday: "இன்றைய ஆர்டர்கள்",
    activeOrdersDesc: "12 நடப்பில் உள்ளன",
    creditDesc: "4 வியாபாரிகளிடம் வரவுள்ளது",
    voiceOrder: "குரல் ஆர்டர்",
    scanBill: "ரசீது ஸ்கேன்",
    khataLedger: "கணக்கு புத்தகம்",
    recentOrders: "சமீபத்திய குரல் ஆர்டர்கள்",
    viewAll: "அனைத்தும் காண்க",
    dueBalance: "நிலுவை தொகை",
    voiceFirstTitle: "இயல்பாகப் பேசி ஆர்டர் எடுக்கவும்",
    voiceFirstDesc: "படிவம் ஏதுமின்றி வாடிக்கையாளர், சரக்கு, அளவு மற்றும் கடன்களை நேரடியாகப் பதிவு செய்யுங்கள்.",
    listening: "கேட்கிறது... பொருள், அளவு மற்றும் வாடிக்கையாளர் பெயர் சொல்லவும்",
    readyMic: "பேசத் தயாராக உள்ளது",
    pipelineTitle: "சார்வம் AI பகுப்பாய்வு முறைமை",
    analyzing: "பகுப்பாய்வு நடக்கிறது",
    verified: "பதிவு செய்யப்பட்டது",
    sttLabel: "சாரஸ் பேச்சு-எழுத்து மாற்றம் (STT)",
    sttSample: "ரமேஷ் கடைக்கு நாளைக்கு 6 பெட்டி ஸ்ப்ரைட், 4 கோக், 20 லிம்கா அனுப்பவும். பழைய பாக்கி 12,500 நிலுவையில் உள்ளது.",
    llmLabel: "இண்டிக் LLM தரவு பிரித்தெடுத்தல்",
    llmSample: "வாடிக்கையாளர்: ரமேஷ் ஸ்டோர் • 6 ஸ்ப்ரைட், 4 கோக், 20 லிம்கா • பாக்கி: ₹12,500",
    clarificationTitle: "விளக்கம் தேவைப்படுகிறது:",
    clarificationPrompt: "20 லிம்கா பாட்டில்களா அல்லது 20 பெட்டிகளா (crates)?",
    bottles: "20 பாட்டில்கள்",
    crates: "20 பெட்டிகள்",
    ledgerSuccess: "கணக்கு புத்தகம் வெற்றிகரமாக புதுப்பிக்கப்பட்டது",
    listenBtn: "ஆடியோ கேட்க",
    replayBtn: "மீண்டும் கேட்க",
    ordersMgmt: "ஆர்டர்கள் மேலாண்மை",
    allOrdersDesc: "பதிவு செய்யப்பட்ட மற்றும் அனுப்பப்பட்ட பொருட்கள்",
    scanTitle: "காகித ரசீது & பில் ஸ்கேனர்",
    scanDesc: "விஷன் OCR மூலம் கையால் எழுதப்பட்ட ரசீதுகள் மற்றும் சப்ளையர் பில்களை நேரடியாகக் கணக்கில் சேர்க்கலாம்.",
    captureBtn: "படம் எடுத்து சரிபார்க்கவும்",
    retailType: "மளிகை & நுகர்பொருள் சில்லறை வணிகம்",
    voiceLang: "பேச்சு மொழி",
    indicModel: "சார்வம் இண்டிக் AI மாடல்",
    paymentQr: "கட்டண QR / UPI",
    switchMerchant: "கடையை மாற்றவும்",
    ttsConfirmation: "ரமேஷ் கடைக்கான ஆர்டர் பதிவு செய்யப்பட்டது: 6 பெட்டி ஸ்ப்ரைட், 4 கோக் மற்றும் 20 லிம்கா. முந்தைய பாக்கி பன்னிரண்டாயிரத்து ஐந்நூறு ரூபாய் நிலுவையில் உள்ளது.",
    navHome: "முகப்பு",
    navOrders: "ஆர்டர்கள்",
    navSpeak: "பேசுக",
    navLedger: "கணக்கு",
    navProfile: "சுயவிவரம்"
  }
};

const INITIAL_ORDERS = [
  {
    id: "ORD-041",
    customer: "Ramesh Store",
    phone: "+91 98765 43210",
    items: [
      { name: "Sprite", qty: "6 crates" },
      { name: "Coke", qty: "4 crates" },
      { name: "Limca", qty: "20 bottles" }
    ],
    delivery: "Tomorrow",
    totalAmount: 18400,
    pendingDue: 12500,
    status: "Confirmed",
    timestamp: "10 mins ago",
    source: "Voice STT"
  },
  {
    id: "ORD-040",
    customer: "Iqbal General Store",
    phone: "+91 98450 12345",
    items: [
      { name: "Flour 10kg", qty: "5 bags" },
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
      { name: "Detergent Powder 1kg", qty: "10 packs" },
      { name: "Dishwash Bar", qty: "2 cartons" }
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
  const [lang, setLang] = useState("en"); // 'en' | 'hinglish' | 'hi' | 'ta'
  const [activeTab, setActiveTab] = useState("home"); // 'home' | 'record' | 'orders' | 'ledger' | 'profile' | 'scan'
  const [isRecording, setIsRecording] = useState(false);
  const [recordTimer, setRecordTimer] = useState(0);
  const [processingStep, setProcessingStep] = useState(null); // 'stt' | 'llm' | 'clarify' | 'tts' | 'done'
  const [orders, setOrders] = useState(INITIAL_ORDERS);
  const [audioPlayed, setAudioPlayed] = useState(false);
  const [clarificationNeeded, setClarificationNeeded] = useState(false);
  const [orderFilter, setOrderFilter] = useState("all");

  const timerRef = useRef(null);
  const t = TRANSLATIONS[lang];

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
          { name: "Sprite", qty: "6 crates" },
          { name: "Coke", qty: "4 crates" },
          { name: "Limca", qty: choice === "crates" ? "20 crates" : "20 bottles" }
        ],
        delivery: "Tomorrow",
        totalAmount: 14200,
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
    <div className="flex justify-center min-h-screen bg-[#F4F1EA] text-[#0A3323] font-sans antialiased selection:bg-[#C49B4C] selection:text-[#0A3323]">
      {/* Mobile-first frame */}
      <div className="w-full max-w-md bg-[#FAF9F5] border-x border-[#E2D2B4] flex flex-col min-h-screen shadow-xl relative pb-20 overflow-hidden">
        
        {/* Soft background ambient gradient meshes */}
        <div className="absolute top-[-10%] left-[-20%] w-[380px] h-[380px] bg-gradient-to-br from-[#E2D2B4]/40 to-[#D3968C]/20 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-[20%] right-[-25%] w-[320px] h-[320px] bg-gradient-to-tr from-[#839958]/20 to-[#C49B4C]/25 rounded-full blur-3xl pointer-events-none" />

        {/* Top App Header with Multi-Language Switcher (EN, Hinglish, हिंदी, தமிழ்) */}
        <header className="px-3.5 py-3 border-b border-[#E2D2B4] bg-[#FAF9F5]/90 backdrop-blur-md sticky top-0 z-20 flex justify-between items-center shadow-sm">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#7A2038] to-[#421C3B] p-0.5 shadow-sm flex items-center justify-center flex-shrink-0">
              <div className="w-full h-full bg-[#FAF9F5] rounded-[6px] flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-[#7A2038]" />
              </div>
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-tight text-[#0A3323] flex items-center gap-1">
                {t.appTitle} <span className="text-[#7A2038] font-serif italic">{t.appSubtitle}</span>
              </h1>
              <p className="text-[8.5px] text-[#0A4F54] font-semibold tracking-wider uppercase">
                {t.tagline}
              </p>
            </div>
          </div>

          {/* 4-Language Selector Pills */}
          <div className="flex items-center gap-1">
            <div className="flex items-center bg-[#E2D2B4]/60 border border-[#C49B4C]/40 rounded-lg p-0.5 text-[10.5px] font-semibold">
              <button
                onClick={() => setLang("en")}
                className={`px-1.5 py-0.5 rounded transition ${
                  lang === "en"
                    ? "bg-[#0A4F54] text-[#FAF9F5] shadow-xs"
                    : "text-[#0A3323] hover:text-[#7A2038]"
                }`}
              >
                EN
              </button>
              <button
                onClick={() => setLang("hinglish")}
                className={`px-1.5 py-0.5 rounded transition ${
                  lang === "hinglish"
                    ? "bg-[#0A4F54] text-[#FAF9F5] shadow-xs"
                    : "text-[#0A3323] hover:text-[#7A2038]"
                }`}
              >
                Hinglish
              </button>
              <button
                onClick={() => setLang("hi")}
                className={`px-1.5 py-0.5 rounded transition ${
                  lang === "hi"
                    ? "bg-[#0A4F54] text-[#FAF9F5] shadow-xs"
                    : "text-[#0A3323] hover:text-[#7A2038]"
                }`}
              >
                हिंदी
              </button>
              <button
                onClick={() => setLang("ta")}
                className={`px-1.5 py-0.5 rounded transition ${
                  lang === "ta"
                    ? "bg-[#0A4F54] text-[#FAF9F5] shadow-xs"
                    : "text-[#0A3323] hover:text-[#7A2038]"
                }`}
              >
                தமிழ்
              </button>
            </div>

            <button 
              onClick={() => setActiveTab("profile")}
              className="w-7 h-7 rounded-full bg-gradient-to-br from-[#7A2038] to-[#421C3B] text-[#FAF9F5] font-bold text-xs flex items-center justify-center shadow-sm flex-shrink-0"
            >
              R
            </button>
          </div>
        </header>

        {/* Dynamic Main Body Content */}
        <main className="flex-1 p-4 overflow-y-auto space-y-4 relative z-10">
          
          {/* ================= HOME VIEW ================= */}
          {activeTab === "home" && (
            <div className="space-y-4">
              {/* Welcome Hero Banner */}
              <div className="relative rounded-3xl p-5 border border-[#C49B4C]/40 bg-gradient-to-br from-[#FAF9F5] via-[#F7F4D5] to-[#E2D2B4]/50 shadow-md overflow-hidden">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-[10px] uppercase tracking-widest text-[#7A2038] font-bold bg-[#E2D2B4]/60 border border-[#C49B4C]/40 px-2.5 py-0.5 rounded-full inline-block mb-2">
                      {t.storeActive}
                    </span>
                    <h2 className="text-lg font-serif text-[#0A3323] font-bold">
                      {t.storeName}
                    </h2>
                    <p className="text-xs text-[#0A3323]/75 mt-0.5">
                      {t.storeDesc}
                    </p>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-[#0A4F54]/15 flex items-center justify-between">
                  <span className="text-xs text-[#0A3323]/80 font-medium">{t.tapToRecord}</span>
                  <button
                    onClick={() => setActiveTab("record")}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-[#7A2038] to-[#421C3B] text-[#FAF9F5] font-semibold text-xs shadow-md hover:opacity-95 transition"
                  >
                    <Mic className="w-3.5 h-3.5" />
                    {t.speakNow}
                  </button>
                </div>
              </div>

              {/* Financial & Operational Stat Highlights */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-[#FAF9F5] p-3.5 rounded-2xl border border-[#D3968C]/50 shadow-sm">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-[10px] text-[#7A2038] uppercase font-bold tracking-wider">{t.pendingCredit}</span>
                    <TrendingUp className="w-4 h-4 text-[#7A2038]" />
                  </div>
                  <p className="text-lg font-bold font-serif text-[#0A3323]">₹26,515</p>
                  <p className="text-[10px] text-[#0A3323]/60 mt-0.5">{t.creditDesc}</p>
                </div>

                <div className="bg-[#FAF9F5] p-3.5 rounded-2xl border border-[#839958]/50 shadow-sm">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-[10px] text-[#0A4F54] uppercase font-bold tracking-wider">{t.ordersToday}</span>
                    <Package className="w-4 h-4 text-[#0A4F54]" />
                  </div>
                  <p className="text-lg font-bold font-serif text-[#0A3323]">{t.activeOrdersDesc}</p>
                  <p className="text-[10px] text-[#0A3323]/60 mt-0.5">₹38,200 total</p>
                </div>
              </div>

              {/* Quick Actions Bar */}
              <div className="grid grid-cols-3 gap-2">
                <button
                  onClick={() => setActiveTab("record")}
                  className="p-3 bg-[#FAF9F5] border border-[#0A4F54]/20 rounded-xl flex flex-col items-center justify-center gap-1.5 hover:border-[#7A2038]/50 shadow-xs transition"
                >
                  <div className="w-8 h-8 rounded-lg bg-[#0A4F54]/10 flex items-center justify-center text-[#0A4F54]">
                    <Mic className="w-4 h-4" />
                  </div>
                  <span className="text-[10px] font-semibold text-[#0A3323]">{t.voiceOrder}</span>
                </button>

                <button
                  onClick={() => setActiveTab("scan")}
                  className="p-3 bg-[#FAF9F5] border border-[#0A4F54]/20 rounded-xl flex flex-col items-center justify-center gap-1.5 hover:border-[#7A2038]/50 shadow-xs transition"
                >
                  <div className="w-8 h-8 rounded-lg bg-[#7A2038]/10 flex items-center justify-center text-[#7A2038]">
                    <Camera className="w-4 h-4" />
                  </div>
                  <span className="text-[10px] font-semibold text-[#0A3323]">{t.scanBill}</span>
                </button>

                <button
                  onClick={() => setActiveTab("ledger")}
                  className="p-3 bg-[#FAF9F5] border border-[#0A4F54]/20 rounded-xl flex flex-col items-center justify-center gap-1.5 hover:border-[#7A2038]/50 shadow-xs transition"
                >
                  <div className="w-8 h-8 rounded-lg bg-[#839958]/20 flex items-center justify-center text-[#0A4F54]">
                    <Receipt className="w-4 h-4" />
                  </div>
                  <span className="text-[10px] font-semibold text-[#0A3323]">{t.khataLedger}</span>
                </button>
              </div>

              {/* Recent Orders Overview on Home */}
              <div className="space-y-2.5 pt-1">
                <div className="flex justify-between items-center px-1">
                  <h3 className="text-xs uppercase tracking-wider text-[#7A2038] font-bold">
                    {t.recentOrders}
                  </h3>
                  <button
                    onClick={() => setActiveTab("orders")}
                    className="text-[11px] text-[#0A4F54] font-semibold flex items-center gap-0.5 hover:underline"
                  >
                    {t.viewAll} ({orders.length}) <ChevronRight className="w-3 h-3" />
                  </button>
                </div>

                {orders.slice(0, 2).map((item) => (
                  <div
                    key={item.id}
                    className="p-3 bg-[#FAF9F5] border border-[#E2D2B4] rounded-xl flex items-center justify-between shadow-sm"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-[#0A3323]">{item.customer}</span>
                        <span className="text-[9px] font-mono text-[#7A2038] bg-[#D3968C]/20 border border-[#D3968C]/40 px-1 py-0.2 rounded font-semibold">
                          {item.id}
                        </span>
                      </div>
                      <p className="text-[11px] text-[#0A3323]/70 mt-0.5">
                        {item.items.map((it) => `${it.qty} ${it.name}`).join(", ")}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs font-mono font-bold text-[#7A2038]">
                        ₹{item.pendingDue.toLocaleString("en-IN")}
                      </p>
                      <span className="text-[9px] text-[#0A4F54] font-semibold">{item.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ================= VOICE ORDER VIEW ================= */}
          {activeTab === "record" && (
            <div className="space-y-4">
              <div className="relative rounded-3xl p-6 border border-[#C49B4C]/40 bg-gradient-to-b from-[#FAF9F5] via-[#F7F4D5] to-[#E2D2B4]/40 text-center overflow-hidden shadow-md">
                <div className="relative z-10">
                  <span className="text-[11px] uppercase tracking-widest text-[#7A2038] font-bold bg-[#E2D2B4]/70 border border-[#C49B4C]/50 px-3 py-1 rounded-full inline-block mb-3">
                    {t.voiceOrder}
                  </span>
                  <h2 className="text-xl font-serif text-[#0A3323] font-bold tracking-tight leading-tight">
                    {t.voiceFirstTitle}
                  </h2>
                  <p className="text-xs text-[#0A3323]/75 max-w-xs mx-auto mt-1 mb-8">
                    {t.voiceFirstDesc}
                  </p>

                  <div className="flex justify-center items-center my-6">
                    <div className="relative flex items-center justify-center">
                      {isRecording && (
                        <>
                          <div className="absolute w-36 h-36 rounded-full border border-[#D3968C]/70 animate-ping opacity-60 pointer-events-none" />
                          <div className="absolute w-44 h-44 rounded-full border border-[#C49B4C]/50 animate-pulse pointer-events-none" />
                        </>
                      )}

                      <button
                        onClick={toggleRecording}
                        className={`relative z-10 flex items-center justify-center w-24 h-24 rounded-full transition-all duration-500 shadow-xl focus:outline-none ${
                          isRecording
                            ? "bg-gradient-to-br from-[#7A2038] via-[#D3968C] to-[#421C3B] shadow-[0_0_35px_rgba(122,32,56,0.35)] scale-110"
                            : "bg-gradient-to-br from-[#0A4F54] via-[#105666] to-[#0A3323] hover:from-[#105666] hover:to-[#0A4F54] shadow-[0_0_25px_rgba(10,79,84,0.25)] border-2 border-[#C49B4C]"
                        }`}
                      >
                        {isRecording ? (
                          <MicOff className="w-9 h-9 text-[#FAF9F5] animate-pulse" />
                        ) : (
                          <Mic className="w-9 h-9 text-[#FAF9F5]" />
                        )}
                      </button>
                    </div>
                  </div>

                  <div className="inline-flex items-center space-x-2 bg-[#FAF9F5] border border-[#0A4F54]/25 px-3.5 py-1.5 rounded-full mt-2 shadow-xs">
                    <span className={`w-2 h-2 rounded-full ${isRecording ? "bg-[#7A2038] animate-ping" : "bg-[#839958]"}`} />
                    <span className="text-xs text-[#0A3323] font-medium font-mono">
                      {isRecording
                        ? `Recording... 00:${recordTimer < 10 ? `0${recordTimer}` : recordTimer}`
                        : t.readyMic}
                    </span>
                  </div>
                </div>
              </div>

              {processingStep && (
                <div className="bg-[#FAF9F5] border border-[#C49B4C]/40 rounded-2xl p-4.5 space-y-3.5 shadow-md">
                  <div className="flex items-center justify-between text-xs font-bold text-[#0A3323] border-b border-[#E2D2B4] pb-2.5">
                    <span className="flex items-center gap-1.5 text-[#7A2038]">
                      <Sparkles className="w-3.5 h-3.5" />
                      {t.pipelineTitle}
                    </span>
                    <span className="text-[10px] font-mono uppercase text-[#0A4F54] bg-[#839958]/20 px-2 py-0.5 rounded border border-[#839958]/40 font-bold">
                      {processingStep === "done" ? t.verified : t.analyzing}
                    </span>
                  </div>

                  <div className="flex items-start space-x-3">
                    <div className="mt-0.5">
                      {processingStep === "stt" ? (
                        <div className="w-4 h-4 border-2 border-[#7A2038] border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <CheckCircle2 className="w-4 h-4 text-[#0A4F54]" />
                      )}
                    </div>
                    <div className="flex-1">
                      <p className="text-xs font-bold text-[#0A3323]">
                        {t.sttLabel}
                      </p>
                      <p className="text-[11px] text-[#0A3323]/70 italic font-serif mt-0.5">
                        "{t.sttSample}"
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start space-x-3">
                    <div className="mt-0.5">
                      {processingStep === "llm" ? (
                        <div className="w-4 h-4 border-2 border-[#7A2038] border-t-transparent rounded-full animate-spin" />
                      ) : processingStep === "stt" ? (
                        <div className="w-4 h-4 rounded-full border border-[#0A4F54]/30" />
                      ) : (
                        <CheckCircle2 className="w-4 h-4 text-[#0A4F54]" />
                      )}
                    </div>
                    <div className="flex-1">
                      <p className="text-xs font-bold text-[#0A3323]">
                        {t.llmLabel}
                      </p>
                      <p className="text-[11px] text-[#7A2038] font-mono font-medium mt-0.5">
                        {t.llmSample}
                      </p>
                    </div>
                  </div>

                  {clarificationNeeded && (
                    <div className="bg-[#D3968C]/25 border border-[#7A2038]/30 rounded-xl p-3.5 my-2 space-y-2.5">
                      <div className="flex items-center space-x-2 text-[#7A2038] text-xs font-bold">
                        <AlertCircle className="w-4 h-4 flex-shrink-0" />
                        <span>{t.clarificationTitle}</span>
                      </div>
                      <p className="text-xs text-[#0A3323]">
                        {t.clarificationPrompt}
                      </p>
                      <div className="flex gap-2 pt-1">
                        <button
                          onClick={() => resolveClarification("bottles")}
                          className="flex-1 py-1.5 px-3 bg-[#0A4F54] hover:bg-[#105666] text-[#FAF9F5] rounded-lg text-xs font-bold transition shadow-sm"
                        >
                          {t.bottles}
                        </button>
                        <button
                          onClick={() => resolveClarification("crates")}
                          className="flex-1 py-1.5 px-3 bg-[#7A2038] hover:bg-[#421C3B] text-[#FAF9F5] rounded-lg text-xs font-bold transition shadow-sm"
                        >
                          {t.crates}
                        </button>
                      </div>
                    </div>
                  )}

                  {processingStep === "done" && (
                    <div className="pt-2.5 border-t border-[#E2D2B4] flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Check className="w-4 h-4 text-[#0A4F54]" />
                        <span className="text-xs text-[#0A3323] font-bold">
                          {t.ledgerSuccess}
                        </span>
                      </div>
                      <button
                        onClick={playTTSFeedback}
                        className="flex items-center space-x-1 text-xs bg-[#0A4F54]/10 hover:bg-[#0A4F54]/20 text-[#0A4F54] font-bold px-2.5 py-1 rounded-md border border-[#0A4F54]/30 transition"
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
                  <h2 className="text-sm font-serif font-bold text-[#0A3323]">
                    {t.ordersMgmt}
                  </h2>
                  <p className="text-[10px] text-[#0A4F54] font-medium">{t.allOrdersDesc}</p>
                </div>
                <span className="text-xs font-mono text-[#7A2038] bg-[#D3968C]/20 px-2 py-0.5 rounded border border-[#D3968C]/40 font-bold">
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
                        ? "bg-[#0A4F54] text-[#FAF9F5] border-[#0A4F54] shadow-xs"
                        : "bg-[#FAF9F5] text-[#0A3323]/80 border-[#E2D2B4] hover:border-[#0A4F54]"
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
                    className="p-4 bg-[#FAF9F5] border border-[#E2D2B4] rounded-2xl space-y-2 shadow-sm"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-sm font-serif font-bold text-[#0A3323]">
                            {order.customer}
                          </h4>
                          <span className="text-[9px] font-mono text-[#7A2038] bg-[#D3968C]/20 px-1.5 py-0.2 rounded border border-[#D3968C]/40 font-bold">
                            {order.id}
                          </span>
                        </div>
                        <p className="text-[10px] text-[#0A3323]/60 flex items-center gap-1 mt-0.5">
                          <Phone className="w-2.5 h-2.5 text-[#0A4F54]" /> {order.phone}
                        </p>
                      </div>
                      <span className="text-[10px] font-bold text-[#0A4F54] bg-[#839958]/20 px-2 py-0.5 rounded-full border border-[#839958]/30">
                        {order.status}
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-1 py-1">
                      {order.items.map((it, idx) => (
                        <span
                          key={idx}
                          className="bg-[#E2D2B4]/50 text-[#0A3323] border border-[#C49B4C]/40 px-2 py-0.5 rounded text-[10px] font-mono font-medium"
                        >
                          {it.qty} {it.name}
                        </span>
                      ))}
                    </div>

                    <div className="pt-2 border-t border-[#E2D2B4] flex justify-between items-center text-[10px] text-[#0A3323]/70">
                      <span>Source: {order.source}</span>
                      <span className="font-mono text-[#0A3323] font-bold">
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
                  <h3 className="text-xs font-bold uppercase tracking-wider text-[#7A2038]">
                    {t.khataLedger}
                  </h3>
                  <p className="text-[10px] text-[#0A4F54] font-medium">{t.creditDesc}</p>
                </div>
                <span className="text-[11px] text-[#0A4F54] font-mono font-bold">
                  {orders.length} Records
                </span>
              </div>

              <div className="space-y-2.5">
                {orders.map((item) => (
                  <div
                    key={item.id}
                    className="p-4 bg-[#FAF9F5] border border-[#E2D2B4] rounded-2xl shadow-sm hover:border-[#0A4F54]/40 transition"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center space-x-2">
                          <h4 className="text-sm font-serif font-bold text-[#0A3323]">
                            {item.customer}
                          </h4>
                          <span className="text-[9px] font-mono text-[#7A2038] bg-[#D3968C]/20 border border-[#D3968C]/40 px-1.5 py-0.2 rounded font-bold">
                            {item.id}
                          </span>
                        </div>
                        <div className="text-[11px] text-[#0A3323]/80 mt-1.5 space-x-1 flex flex-wrap">
                          {item.items.map((it, idx) => (
                            <span
                              key={idx}
                              className="bg-[#E2D2B4]/40 text-[#0A3323] border border-[#C49B4C]/30 px-2 py-0.5 rounded text-[10px] mr-1 mb-1 font-mono"
                            >
                              {it.qty} {it.name}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-xs font-mono font-bold text-[#7A2038]">
                          ₹{item.pendingDue.toLocaleString("en-IN")}
                        </p>
                        <p className="text-[10px] text-[#0A3323]/60">{t.dueBalance}</p>
                      </div>
                    </div>

                    <div className="mt-3 pt-2.5 border-t border-[#E2D2B4] flex items-center justify-between text-[10px] text-[#0A3323]/70">
                      <span className="flex items-center">
                        <Clock className="w-3 h-3 mr-1 text-[#0A4F54]" />
                        Delivery: {item.delivery}
                      </span>
                      <span className="text-[#0A4F54] font-bold">
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
              <div className="w-20 h-20 bg-gradient-to-br from-[#E2D2B4] to-[#FAF9F5] border-2 border-dashed border-[#7A2038]/50 rounded-3xl flex items-center justify-center mx-auto text-[#7A2038] shadow-md">
                <Camera className="w-9 h-9" />
              </div>
              <div className="px-4">
                <h3 className="text-base font-serif font-bold text-[#0A3323]">
                  {t.scanTitle}
                </h3>
                <p className="text-xs text-[#0A3323]/70 max-w-xs mx-auto mt-1.5">
                  {t.scanDesc}
                </p>
              </div>

              <div className="pt-2 px-6">
                <button
                  onClick={() => setActiveTab("ledger")}
                  className="w-full py-3 px-4 bg-gradient-to-r from-[#0A4F54] to-[#105666] hover:opacity-95 text-[#FAF9F5] rounded-xl text-xs font-bold transition shadow-md flex items-center justify-center gap-2"
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
              <div className="p-5 rounded-3xl border border-[#C49B4C]/40 bg-gradient-to-br from-[#FAF9F5] via-[#F7F4D5] to-[#E2D2B4]/40 flex items-center gap-4 shadow-sm">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#7A2038] to-[#421C3B] text-[#FAF9F5] font-serif font-bold text-xl flex items-center justify-center shadow-md border-2 border-[#FAF9F5]">
                  RP
                </div>
                <div>
                  <h3 className="text-base font-serif font-bold text-[#0A3323]">
                    {t.storeName}
                  </h3>
                  <p className="text-xs text-[#7A2038] font-bold flex items-center gap-1">
                    <Store className="w-3 h-3" /> {t.retailType}
                  </p>
                  <p className="text-[10px] text-[#0A3323]/60 mt-0.5">GSTIN: 27AABCR1234F1Z9</p>
                </div>
              </div>

              <div className="bg-[#FAF9F5] border border-[#E2D2B4] rounded-2xl divide-y divide-[#E2D2B4] shadow-xs">
                <div className="p-3.5 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-7 h-7 rounded-lg bg-[#0A4F54]/10 flex items-center justify-center text-[#0A4F54]">
                      <Languages className="w-3.5 h-3.5" />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-[#0A3323]">{t.voiceLang}</p>
                      <p className="text-[10px] text-[#0A3323]/60">
                        {lang === "en" ? "English" : lang === "hinglish" ? "Hinglish" : lang === "hi" ? "हिंदी (Hindi)" : "தமிழ் (Tamil)"}
                      </p>
                    </div>
                  </div>
                  <span className="text-[10px] text-[#0A4F54] font-bold bg-[#839958]/20 px-2 py-0.5 rounded border border-[#839958]/30">
                    Active
                  </span>
                </div>

                <div className="p-3.5 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-7 h-7 rounded-lg bg-[#7A2038]/10 flex items-center justify-center text-[#7A2038]">
                      <ShieldCheck className="w-3.5 h-3.5" />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-[#0A3323]">{t.indicModel}</p>
                      <p className="text-[10px] text-[#0A3323]/60">Saaras STT & Bulbul TTS</p>
                    </div>
                  </div>
                  <span className="text-[10px] text-[#7A2038] font-mono font-bold">v2.4</span>
                </div>

                <div className="p-3.5 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-7 h-7 rounded-lg bg-[#839958]/20 flex items-center justify-center text-[#0A4F54]">
                      <CreditCard className="w-3.5 h-3.5" />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-[#0A3323]">{t.paymentQr}</p>
                      <p className="text-[10px] text-[#0A3323]/60">rajeshprovisions@upi</p>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-[#0A3323]/40" />
                </div>
              </div>

              <div className="p-3 bg-[#FAF9F5] border border-[#E2D2B4] rounded-2xl text-[11px] text-[#0A3323]/70 space-y-1">
                <p className="text-[#7A2038] font-bold">Team Binary Brains</p>
                <p>Chinmay Agarwal • Jayesh Motwani • Pushpmitra • Krishnave</p>
              </div>

              <button 
                onClick={() => setActiveTab("home")}
                className="w-full py-2.5 border border-[#7A2038]/40 rounded-xl text-xs font-bold text-[#7A2038] hover:bg-[#7A2038]/10 flex items-center justify-center gap-1.5 transition"
              >
                <LogOut className="w-3.5 h-3.5" /> {t.switchMerchant}
              </button>
            </div>
          )}
        </main>

        {/* Bottom 5-Tab Navigation Bar in Light Mode */}
        <nav className="absolute bottom-0 left-0 right-0 h-16 bg-[#FAF9F5]/95 border-t border-[#E2D2B4] backdrop-blur-md px-3 flex justify-around items-center z-30 shadow-lg">
          <button
            onClick={() => setActiveTab("home")}
            className={`flex flex-col items-center justify-center space-y-1 transition ${
              activeTab === "home" ? "text-[#7A2038] font-bold" : "text-[#0A3323]/50 hover:text-[#0A3323]"
            }`}
          >
            <Home className="w-4 h-4" />
            <span className="text-[9px]">{t.navHome}</span>
          </button>

          <button
            onClick={() => setActiveTab("orders")}
            className={`flex flex-col items-center justify-center space-y-1 transition ${
              activeTab === "orders" ? "text-[#7A2038] font-bold" : "text-[#0A3323]/50 hover:text-[#0A3323]"
            }`}
          >
            <ShoppingBag className="w-4 h-4" />
            <span className="text-[9px]">{t.navOrders}</span>
          </button>

          {/* Centered Floating Voice Mic Button */}
          <button
            onClick={() => setActiveTab("record")}
            className="flex flex-col items-center justify-center -mt-5"
          >
            <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-[#7A2038] via-[#C49B4C] to-[#0A4F54] p-0.5 shadow-md">
              <div className="w-full h-full bg-[#FAF9F5] hover:bg-[#F7F4D5] rounded-full flex items-center justify-center transition">
                <Mic className="w-5 h-5 text-[#7A2038]" />
              </div>
            </div>
            <span className="text-[9px] font-bold text-[#7A2038] mt-1">{t.navSpeak}</span>
          </button>

          <button
            onClick={() => setActiveTab("ledger")}
            className={`flex flex-col items-center justify-center space-y-1 transition ${
              activeTab === "ledger" ? "text-[#7A2038] font-bold" : "text-[#0A3323]/50 hover:text-[#0A3323]"
            }`}
          >
            <Receipt className="w-4 h-4" />
            <span className="text-[9px]">{t.navLedger}</span>
          </button>

          <button
            onClick={() => setActiveTab("profile")}
            className={`flex flex-col items-center justify-center space-y-1 transition ${
              activeTab === "profile" ? "text-[#7A2038] font-bold" : "text-[#0A3323]/50 hover:text-[#0A3323]"
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