/* =========================================================
   SLIDES DATA — الجلسة الثانية: Tool Calling
   -----------------------------------------------------------
   نفس بنية session1/slides.js — كل slide = { duration, durationText, html }.
   لإضافة/تعديل شريحة: عدّل هذا المصفوفة فقط، script.js يعيد
   الرسم تلقائيًا.
========================================================= */

const SLIDES = [

// ---------- 1. Title ----------
{
  duration: 2,
  html: `
  <div class="slide-inner title-slide">
    <span class="eyebrow en">AI Agents Course</span>
    <h1 class="slide-title">الجلسة الثانية</h1>
    <h2 class="slide-subtitle en">Tool Calling: From "Text Generation" to "Problem Solving"</h2>
    <p class="slide-desc">جلسة نظرية + عملية (<span class="en">hands-on</span>) — المدة: ساعتان.</p>
    <div class="title-meta">
      <div class="meta-pill">⏱️ مدة الجلسة: ساعتان</div>
      <div class="meta-pill">📚 Based on IBM <span class="en">"AI agents and Agentic AI workflows"</span> — Coursera</div>
    </div>
  </div>`
},

// ---------- 2. Objectives ----------
{
  duration: 2,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Session Objectives</span>
    <h1 class="slide-title">أهداف الجلسة</h1>
    <div class="slide-body">
      <ul class="bullet-list">
        <li><span class="num">1</span>فهم ما هو <span class="en">Tool Calling</span> ولماذا تحتاجه النماذج اللغوية.</li>
        <li><span class="num">2</span>التمييز بين <span class="en">Tool Calling</span> و<span class="en">Function Calling</span>.</li>
        <li><span class="num">3</span>فهم دورة حياة استدعاء الأداة: <span class="en">Tool Call → Execution → Result → Final Response</span>.</li>
        <li><span class="num">4</span>إنشاء <span class="en">Tools</span> مخصصة في <span class="en">LangChain</span> بثلاث طرق (<span class="en">@tool</span>، <span class="en">Tool class</span>، <span class="en">StructuredTool</span>).</li>
        <li><span class="num">5</span>تطبيق <span class="en">Manual Tool Calling</span> والتحكم الكامل بالتنفيذ (<span class="en">validation + filtering</span>).</li>
        <li><span class="num">6</span>بناء <span class="en">Agent</span> تفاعلي حقيقي يستخدم عدة أدوات.</li>
        <li><span class="num">7</span>(إذا سمح الوقت) فهم أساسيات <span class="en">RAG</span> و<span class="en">Embeddings</span> و<span class="en">Vector Databases</span>.</li>
      </ul>
    </div>
  </div>`
},

// ---------- 3. Agenda / timeline ----------
{
  duration: 2,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Agenda</span>
    <h1 class="slide-title">خطة الجلسة والتوقيت</h1>
    <div class="slide-body">
      <div class="timeline-wrap">
        <span class="timeline-total">الأساسي: ~١٠٠ دقيقة · Stretch (RAG): +٢٠ دقيقة إن سمح الوقت</span>
        <ul class="timeline-list">
          <li class="timeline-item"><span class="timeline-topic"><span class="en">LLMs</span> بدون أدوات: الآلة المعصوبة العينين</span><span class="timeline-time">8′</span></li>
          <li class="timeline-item"><span class="timeline-topic">ما الذي تفتحه الأدوات: 4 قدرات</span><span class="timeline-time">10′</span></li>
          <li class="timeline-item"><span class="timeline-topic"><span class="en">Hallucination</span> ومثال الآلة الحاسبة</span><span class="timeline-time">5′</span></li>
          <li class="timeline-item"><span class="timeline-topic">تشريح الـ <span class="en">Tool</span>: Name / Description / Parameters</span><span class="timeline-time">5′</span></li>
          <li class="timeline-item"><span class="timeline-topic">دورة حياة <span class="en">Tool Call</span> (الـ workflow الكامل)</span><span class="timeline-time">10′</span></li>
          <li class="timeline-item"><span class="timeline-topic"><span class="en">Tool Calling vs Function Calling</span></span><span class="timeline-time">3′</span></li>
          <li class="timeline-item"><span class="timeline-topic">🧪 <span class="en">Lab 1:</span> إعداد البيئة + Hello World</span><span class="timeline-time">10′</span></li>
          <li class="timeline-item"><span class="timeline-topic">طرق إنشاء <span class="en">Tools</span> في <span class="en">LangChain</span></span><span class="timeline-time">8′</span></li>
          <li class="timeline-item"><span class="timeline-topic">🧪 <span class="en">Lab 2:</span> بناء أدوات مخصصة وربطها بالنموذج</span><span class="timeline-time">15′</span></li>
          <li class="timeline-item"><span class="timeline-topic"><span class="en">Manual Tool Calling</span>: التحكم الكامل</span><span class="timeline-time">8′</span></li>
          <li class="timeline-item"><span class="timeline-topic">🧪 <span class="en">Lab 3:</span> Agent تفاعلي متعدد الأدوات</span><span class="timeline-time">15′</span></li>
          <li class="timeline-item"><span class="timeline-topic"><span class="en">Built-in Tools</span> و<span class="en">Toolkits</span></span><span class="timeline-time">5′</span></li>
          <li class="timeline-item"><span class="timeline-topic"><span class="en">Structured Outputs</span></span><span class="timeline-time">6′</span></li>
          <li class="timeline-item"><span class="timeline-topic"><span class="en">Quiz</span> + الجلسة القادمة + المراجع</span><span class="timeline-time">5′</span></li>
          <li class="timeline-item"><span class="timeline-topic">⭐ <span class="en">(Stretch) RAG</span>، <span class="en">Embeddings</span>، <span class="en">Vector DBs</span> + مثال عملي</span><span class="timeline-time">+20′</span></li>
        </ul>
      </div>
    </div>
  </div>`
},

// ---------- 4. LLMs without Tool Calling ----------
{
  duration: 4,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">The Starting Point</span>
    <h1 class="slide-title"><span class="en">LLMs</span> بدون <span class="en">Tool Calling</span></h1>
    <p class="slide-desc">قبل أن نضيف أي أداة، لنتذكر ما هو النموذج اللغوي في جوهره:</p>
    <div class="slide-body">
      <div class="note-banner">النماذج اللغوية وحدها هي <span class="en">Pattern Recognition Machines</span> — آلات تمييز أنماط، وليست مصادر حقائق.</div>
      <ul class="bullet-list warning">
        <li><span class="ico">🕰️</span>لا حقائق فورية (<span class="en">No real-time facts</span>) — معرفتها متجمدة عند تاريخ التدريب.</li>
        <li><span class="ico">🔌</span>لا تستطيع الوصول لـ <span class="en">APIs</span> خارجية.</li>
        <li><span class="ico">🌍</span>لا تستطيع التفاعل مع العالم الخارجي أو اتخاذ أي فعل حقيقي.</li>
      </ul>
    </div>
  </div>`
},

// ---------- 5. Blindfolded genius analogy ----------
{
  duration: 4,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Analogy</span>
    <h1 class="slide-title">تشبيه: العبقري المعصوب العينين</h1>
    <p class="slide-desc">تخيل أنك تطلب من شخص خارق الذكاء حل مشكلة واقعية، لكنه:</p>
    <div class="slide-body">
      <div class="icon-grid">
        <div class="icon-card"><div class="icon-big">🙈</div><div class="icon-label en">Blindfolded</div></div>
        <div class="icon-card"><div class="icon-big">🔍</div><div class="icon-label">بدون <span class="en">Google</span></div></div>
        <div class="icon-card"><div class="icon-big">🧮</div><div class="icon-label">بدون <span class="en">Calculator</span></div></div>
        <div class="icon-card"><div class="icon-big">📵</div><div class="icon-label">بدون هاتف</div></div>
      </div>
      <div class="note-banner">مهما كان ذكيًا، قدرته على حل المشاكل الواقعية محدودة جدًا — وهذا بالضبط وضع الـ <span class="en">LLM</span> بدون أدوات.</div>
    </div>
  </div>`
},

// ---------- 6. What do tools open up ----------
{
  duration: 3,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">The Shift</span>
    <h1 class="slide-title">ماذا تفعل الأدوات؟</h1>
    <p class="slide-desc">الأدوات تسمح للـ <span class="en">LLM</span> بالتفاعل مع العالم: إجراء عمليات حسابية، جلب حقائق، تنفيذ أفعال.</p>
    <div class="slide-body">
      <div class="transform-diagram">
        <div class="transform-box from">
          <div class="t-label en">Text Generation</div>
          <div class="t-sub">توليد نص فقط</div>
        </div>
        <div class="transform-arrow-big">→</div>
        <div class="transform-box to">
          <div class="t-label en">Problem Solving</div>
          <div class="t-sub">حل مشاكل حقيقية</div>
        </div>
      </div>
      <div class="note-banner">هذا هو التحول الجوهري الذي يقدمه <span class="en">Tool Calling</span> لبقية الجلسة.</div>
    </div>
  </div>`
},

// ---------- 7. Capability 1: Access private data ----------
{
  duration: 3,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Capability 1 / 4</span>
    <h1 class="slide-title">الوصول لبيانات خاصة <span class="en">(Access Private Data)</span></h1>
    <div class="slide-body">
      <ul class="bullet-list">
        <li><span class="ico">🔒</span>بيانات ليست في الـ <span class="en">input</span> ولا في <span class="en">training data</span> النموذج.</li>
        <li><span class="ico">🗄️</span>مثال: قاعدة بيانات شركتك، ملفاتك الشخصية، سجلات العملاء.</li>
      </ul>
      <div class="note-banner">هذه القدرة هي الأساس الذي يمكّن <span class="en">RAG (Retrieval-Augmented Generation)</span> — سنتوسع فيها لاحقًا إن سمح الوقت.</div>
    </div>
  </div>`
},

// ---------- 8. Capability 2: Multiple modalities ----------
{
  duration: 2,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Capability 2 / 4</span>
    <h1 class="slide-title">تحليل وسائط متعددة <span class="en">(Multiple Modalities)</span></h1>
    <div class="slide-body">
      <div class="cards-grid">
        <div class="card"><div class="card-icon">🖼️</div><div class="card-title en">Vision capabilities</div><div class="card-text">تحليل الصور ومحتواها.</div></div>
        <div class="card"><div class="card-icon">🎙️</div><div class="card-title en">Voice understanding</div><div class="card-text">معالجة وفهم الصوت.</div></div>
        <div class="card"><div class="card-icon">🧬</div><div class="card-title en">Multimodal reasoning</div><div class="card-text">دمج أنواع مدخلات مختلفة في استنتاج واحد.</div></div>
      </div>
    </div>
  </div>`
},

// ---------- 9. Capability 3: Overcome LLM limitations ----------
{
  duration: 3,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Capability 3 / 4</span>
    <h1 class="slide-title">تجاوز حدود النموذج <span class="en">(Overcome LLM Limitations)</span></h1>
    <div class="slide-body">
      <ul class="bullet-list">
        <li><span class="ico">📏</span>الامتداد خارج القيود المدمجة في النموذج نفسه.</li>
        <li><span class="ico">🧠</span>الحفاظ على ذاكرة محادثة عبر الجلسات (<span class="en">Conversational memory across sessions</span>).</li>
        <li><span class="ico">📚</span>معالجة معلومات تتجاوز حجم الـ <span class="en">Context Window</span>.</li>
      </ul>
    </div>
  </div>`
},

// ---------- 10. Capability 4: Control external systems ----------
{
  duration: 2,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Capability 4 / 4</span>
    <h1 class="slide-title">التحكم بأنظمة خارجية <span class="en">(Control External Systems)</span></h1>
    <div class="slide-body">
      <ul class="bullet-list">
        <li><span class="ico">🔗</span>التفاعل مع <span class="en">APIs</span> والبرمجيات والخدمات الرقمية.</li>
        <li><span class="ico">⚡</span>تسمح للـ <span class="en">LLM</span> باتخاذ أفعال (<span class="en">Actions</span>) وليس فقط توليد كلام.</li>
      </ul>
    </div>
  </div>`
},

// ---------- 11. Hallucination + calculator example ----------
{
  duration: 5,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Why It Matters</span>
    <h1 class="slide-title"><span class="en">Hallucination</span> ومثال الآلة الحاسبة</h1>
    <p class="slide-desc">الـ <span class="en">LLM</span> يجيب بناءً على أنماط معروفة → يؤدي إلى <span class="en">Hallucination</span>. مثال: اسأل النموذج "كم حاصل 345 × 123؟"</p>
    <div class="slide-body">
      <div class="compare-grid">
        <div class="compare-col neutral">
          <h3><span class="en">LLM</span> وحده</h3>
          <ul>
            <li>يولّد رقمًا "يبدو صحيحًا" بناءً على النمط.</li>
            <li><span class="en">42,585</span> ❌ — رقم قريب لكنه خاطئ.</li>
          </ul>
        </div>
        <div class="compare-col highlight">
          <h3><span class="en">LLM</span> + <span class="en">Calculator Tool</span></h3>
          <ul>
            <li>يستدعي أداة الآلة الحاسبة بدل التخمين.</li>
            <li><span class="en">42,435</span> ✅ — النتيجة الصحيحة دائمًا.</li>
          </ul>
        </div>
      </div>
      <div class="note-banner">استخدام الأدوات يمنع الـ <span class="en">Hallucination</span> في المهام القابلة للتحقق.</div>
    </div>
  </div>`
},

// ---------- 12. Tools beyond math ----------
{
  duration: 3,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Beyond Math</span>
    <h1 class="slide-title">الأدوات أبعد من الرياضيات</h1>
    <div class="slide-body">
      <div class="cards-grid">
        <div class="card"><div class="card-icon">🌦️</div><div class="card-title en">Web tools</div><div class="card-text">جلب حالة الطقس الفورية.</div></div>
        <div class="card"><div class="card-icon">🐍</div><div class="card-title en">Code tool</div><div class="card-text">كتابة وتنفيذ كود <span class="en">Python</span>.</div></div>
        <div class="card"><div class="card-icon">📰</div><div class="card-title en">Search tool</div><div class="card-text">البحث عن آخر الأخبار.</div></div>
        <div class="card"><div class="card-icon">🗃️</div><div class="card-title en">SQL tool</div><div class="card-text">استعلام بيانات من قاعدة بيانات العمل.</div></div>
      </div>
      <div class="note-banner">تفتح هذه الأدوات قدرات جديدة: الوصول للويب، التفاعل مع قواعد البيانات، التحكم بالتطبيقات، توليد <span class="en">Visualizations</span>.</div>
    </div>
  </div>`
},

// ---------- 13. Agentic workflow future diagram ----------
{
  duration: 2,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">The Bigger Picture</span>
    <h1 class="slide-title">مستقبل الـ <span class="en">Agentic Workflow</span></h1>
    <div class="slide-body">
      <div class="flow-diagram">
        <div class="flow-box">User Query</div>
        <div class="flow-arrow">→</div>
        <div class="flow-box accent">LLM</div>
        <div class="flow-arrow">→</div>
        <div class="flow-box">Tool</div>
        <div class="flow-arrow">→</div>
        <div class="flow-box">Action</div>
        <div class="flow-arrow">→</div>
        <div class="flow-box">Response</div>
      </div>
    </div>
  </div>`
},

// ---------- 14. Tool anatomy in LangChain ----------
{
  duration: 5,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Anatomy</span>
    <h1 class="slide-title">تشريح الـ <span class="en">Tool</span> في <span class="en">LangChain</span></h1>
    <p class="slide-desc">الـ <span class="en">Tool</span> هو ببساطة دالة (<span class="en">Python function</span>) متاحة للنموذج، وله <span class="en">Schema</span> من ثلاثة مكونات:</p>
    <div class="slide-body">
      <div class="schema-box">
        <div class="schema-row"><span class="schema-key">name</span><span class="schema-val">"get_weather" <span class="rtl-note">— معرّف فريد للأداة</span></span></div>
        <div class="schema-row"><span class="schema-key">description</span><span class="schema-val">"Get current weather for a city" <span class="rtl-note">— النموذج يقرر بناءً عليه متى يستخدمها!</span></span></div>
        <div class="schema-row"><span class="schema-key">parameters</span><span class="schema-val">{ city: string } <span class="rtl-note">— المدخلات التي تتوقعها الأداة</span></span></div>
      </div>
      <div class="note-banner">هذا الـ <span class="en">Schema</span> هو ما يمكّن النموذج من فهم متى وكيف يستخدم الأداة.</div>
    </div>
  </div>`
},

// ---------- 15. Tool Call lifecycle ----------
{
  duration: 10,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">The Full Workflow</span>
    <h1 class="slide-title">دورة حياة <span class="en">Tool Call</span>: الـ <span class="en">Workflow</span> الكامل</h1>
    <p class="slide-desc"><strong>نقطة جوهرية:</strong> النموذج <strong>لا ينفّذ</strong> الأداة بنفسه أبدًا — هو فقط يولّد طلبًا منسقًا (<span class="en">structured output / JSON</span>) يحدد اسم الأداة وقيم الـ <span class="en">parameters</span>. التنفيذ الفعلي مسؤولية نظام خارجي.</p>
    <div class="slide-body">
      <div class="workflow-steps">
        <div class="wf-step">
          <div class="wf-index">1</div>
          <div><h4><span class="en">Tool Setup + Question</span></h4><p>نعرّف الأدوات المتاحة ونطرح السؤال: <code>"What's the weather in Paris?"</code></p></div>
        </div>
        <div class="wf-step">
          <div class="wf-index">2</div>
          <div><h4><span class="en">Tool Call</span></h4><p>النموذج يوقف التوليد العادي ويخرج <span class="en">tool call</span> منسق: <code>get_weather("paris")</code></p></div>
        </div>
        <div class="wf-step exec">
          <div class="wf-index">3</div>
          <div><h4><span class="en">Tool Execution</span></h4><p>التطبيق ينفّذ الدالة فعليًا ويحصل على النتيجة: <code>{"temperature": 14}</code></p></div>
        </div>
        <div class="wf-step">
          <div class="wf-index">4</div>
          <div><h4><span class="en">Result Passing</span></h4><p>النتيجة تُعاد للنموذج (<span class="en">ToolMessage</span>) وتصبح جزءًا من سياقه.</p></div>
        </div>
        <div class="wf-step">
          <div class="wf-index">5</div>
          <div><h4><span class="en">Final Response</span></h4><p>النموذج يولّد إجابة طبيعية نهائية: <em>"It's currently 14°C in Paris."</em></p></div>
        </div>
      </div>
    </div>
  </div>`
},

// ---------- 16. Tool Calling vs Function Calling ----------
{
  duration: 3,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Naming</span>
    <h1 class="slide-title"><span class="en">Tool Calling</span> مقابل <span class="en">Function Calling</span></h1>
    <div class="slide-body">
      <ul class="bullet-list">
        <li><span class="ico">🟰</span>المفهومان <strong>متطابقان تقنيًا</strong> — الفرق في التسمية فقط.</li>
        <li><span class="ico">🏷️</span><span class="en">Function Calling</span>: المصطلح الذي روّجته <span class="en">OpenAI</span> في توثيقها.</li>
        <li><span class="ico">🏭</span><span class="en">Tool Calling</span>: المصطلح الصناعي الأعم — تستخدمه <span class="en">Anthropic</span> و<span class="en">LangChain</span> وغيرها.</li>
      </ul>
      <div class="note-banner">نفس المفاهيم، نفس الـ <span class="en">workflow</span>، نفس التنفيذ.</div>
    </div>
  </div>`
},

// ---------- 17. Lab 1: Setup + Hello World ----------
{
  duration: 10,
  html: `
  <div class="slide-inner">
    <span class="lab-badge">🧪 Lab 1</span>
    <h1 class="slide-title">إعداد البيئة + <span class="en">Hello World</span></h1>
    <span class="lab-file">labs/01_hello_world.py</span>
    <div class="slide-body">
      <ul class="bullet-list">
        <li><span class="num">1</span>تثبيت <span class="en">Python 3.11+</span> و<span class="en">Docker Desktop</span>.</li>
        <li><span class="num">2</span>إنشاء <span class="en">virtual environment</span> وتثبيت المكتبات.</li>
        <li><span class="num">3</span>الحصول على <span class="en">HuggingFace API Token</span> (مجاني).</li>
        <li><span class="num">4</span>تشغيل <span class="en">Ollama</span> (نموذج محلي مفتوح المصدر).</li>
        <li><span class="num">5</span>اختبار <span class="en">"Hello World"</span>: أول استدعاء ناجح للنموذج عبر <span class="en">LangChain</span>.</li>
      </ul>
      <div class="note-banner">التفاصيل الكاملة خطوة بخطوة في <span class="en">labs/SETUP.md</span>.</div>
    </div>
  </div>`
},

// ---------- 18. Ways to create tools in LangChain ----------
{
  duration: 8,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Three Ways</span>
    <h1 class="slide-title">طرق إنشاء <span class="en">Tools</span> في <span class="en">LangChain</span></h1>
    <p class="slide-desc">كل الأدوات ترث من <span class="en">BaseTool</span>. ثلاث طرق عملية بالترتيب من الأبسط للأقوى:</p>
    <div class="slide-body">
      <div class="cards-grid">
        <div class="card">
          <div class="card-icon">✨</div>
          <div class="card-title en">@tool decorator</div>
          <div class="card-text">الموصى بها. تحويل أي دالة <span class="en">Python</span> لأداة تلقائيًا — يستنتج الاسم والوصف والـ <span class="en">schema</span> من التوقيع والـ <span class="en">docstring</span>، وينتج <span class="en">StructuredTool</span>.</div>
        </div>
        <div class="card">
          <div class="card-icon">🧰</div>
          <div class="card-title en">Tool class</div>
          <div class="card-text">الطريقة التقليدية — تغليف دالة مع <span class="en">metadata</span> يدوي (مدخل نصي واحد أساسًا).</div>
        </div>
        <div class="card">
          <div class="card-icon">🏗️</div>
          <div class="card-title en">StructuredTool.from_function</div>
          <div class="card-text">الأكثر مرونة — يدعم <span class="en">schemas</span> معقدة و<span class="en">sync/async</span> معًا.</div>
        </div>
      </div>
      <div class="code-block" data-lang="python">
        <div class="code-block-head"><span class="code-dots"><i></i><i></i><i></i></span><span class="code-filename">الطريقة 1 — @tool</span></div>
        <pre class="code-body"><code class="language-python">@tool
def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression."""
    return str(eval(expression))</code></pre>
      </div>
    </div>
  </div>`
},

// ---------- 19. bind_tools snippet (shares Lab 2 time) ----------
{
  duration: null,
  durationText: "ضمن نفس الوقت",
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Binding Tools</span>
    <h1 class="slide-title">ربط الأدوات بالنموذج والاستدعاء</h1>
    <div class="slide-body">
      <div class="code-block" data-lang="python">
        <div class="code-block-head"><span class="code-dots"><i></i><i></i><i></i></span><span class="code-filename">labs/02_custom_tools.py</span></div>
        <pre class="code-body"><code class="language-python">tools = [add_tool, divide_numbers]
llm_with_tools = llm.bind_tools(tools)
response = llm_with_tools.invoke("What is 10 divided by 2?")
# response.tool_calls -> [{'name': 'divide_numbers', 'args': {'a': 10, 'b': 2}, ...}]</code></pre>
      </div>
      <ul class="bullet-list">
        <li><span class="ico">🔗</span><code class="en code">bind_tools</code> تخبر النموذج ما هي الأدوات المتاحة وماذا تحتاج.</li>
        <li><span class="ico">📤</span>النموذج يرد بـ <code class="en code">tool_calls</code> في الـ <span class="en">AIMessage</span> — والتنفيذ علينا نحن.</li>
      </ul>
    </div>
  </div>`
},

// ---------- 20. Lab 2: Custom tools ----------
{
  duration: 15,
  html: `
  <div class="slide-inner">
    <span class="lab-badge">🧪 Lab 2</span>
    <h1 class="slide-title">بناء أدوات مخصصة</h1>
    <span class="lab-file">labs/02_custom_tools.py</span>
    <div class="slide-body">
      <ul class="bullet-list">
        <li><span class="num">1</span>إنشاء 3 أدوات بالطرق الثلاث: <code class="en code">calculator</code> (<span class="en">@tool</span>)، <code class="en code">unit_converter</code> (<span class="en">Tool class</span>)، <code class="en code">currency_tool</code> (<span class="en">StructuredTool</span>).</li>
        <li><span class="num">2</span>فحص الـ <span class="en">schema</span>: <code class="en code">name</code> / <code class="en code">description</code> / <code class="en code">args</code>.</li>
        <li><span class="num">3</span><span class="en">invoke</span> مباشر للأداة للاختبار، ثم <code class="en code">bind_tools</code> وترك النموذج يقرر.</li>
        <li><span class="num">4</span>تمرير النتيجة للنموذج عبر <span class="en">ToolMessage</span> والحصول على إجابة نهائية.</li>
      </ul>
    </div>
  </div>`
},

// ---------- 21. Manual Tool Calling ----------
{
  duration: 8,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Full Control</span>
    <h1 class="slide-title"><span class="en">Manual Tool Calling</span>: التحكم الكامل</h1>
    <p class="slide-desc">لماذا لا ننفذ كل ما يطلبه النموذج تلقائيًا؟ في بيئات الإنتاج نحتاج تحكمًا:</p>
    <div class="slide-body">
      <ul class="bullet-list">
        <li><span class="ico">🔀</span><span class="en">Conditional execution</span>: نحن نقرر هل ننفّذ الـ <span class="en">tool call</span> أصلًا.</li>
        <li><span class="ico">📐</span><span class="en">Custom business logic</span>: قواعد تتجاوز قرار النموذج (مثال: منع الأرقام السالبة).</li>
        <li><span class="ico">🧹</span><span class="en">Tool filtering</span>: الأدوات غير المعروفة تُتخطى.</li>
        <li><span class="ico">🛑</span><span class="en">Custom error handling</span>: رفض استباقي برسالة خطأ واضحة بدل فشل التنفيذ.</li>
      </ul>
      <div class="note-banner">مفاهيم أساسية: <code class="en code">AIMessage.tool_calls</code> / <code class="en code">ToolMessage</code> / <code class="en code">tool_call_id</code> (لمطابقة النتيجة بالطلب) — و<span class="en">validation</span> عبر <span class="en">Pydantic models</span> قبل التنفيذ.</div>
    </div>
  </div>`
},

// ---------- 22. Lab 3: Interactive agent ----------
{
  duration: 15,
  html: `
  <div class="slide-inner">
    <span class="lab-badge">🧪 Lab 3</span>
    <h1 class="slide-title">Agent تفاعلي متعدد الأدوات</h1>
    <span class="lab-file">labs/03_interactive_agent.py</span>
    <div class="slide-body">
      <ul class="bullet-list">
        <li><span class="num">1</span>بناء <span class="en">Agent</span> كامل بحلقة تنفيذ (<span class="en">agent loop</span>): سؤال المستخدم → يقرر الأداة → ننفذ → نعيد النتيجة → إجابة نهائية.</li>
        <li><span class="num">2</span>أدوات الـ <span class="en">Agent</span>: <code class="en code">calculator</code> + <code class="en code">wikipedia</code> + وقت/تاريخ محلي.</li>
        <li><span class="num">3</span><span class="en">Validation</span> يدوي + <span class="en">tool filtering</span> (تطبيق مفاهيم الشريحة السابقة).</li>
        <li><span class="num">4</span>تشغيل تفاعلي من الـ <span class="en">terminal</span> (<span class="en">input loop</span>) مع أمثلة أسئلة جاهزة للتجربة.</li>
      </ul>
    </div>
  </div>`
},

// ---------- 23. Built-in Tools & Toolkits ----------
{
  duration: 5,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Don't Reinvent the Wheel</span>
    <h1 class="slide-title"><span class="en">Built-in Tools</span> و<span class="en">Toolkits</span></h1>
    <p class="slide-desc"><span class="en">LangChain</span> توفر أدوات جاهزة — لا تعيد اختراع العجلة:</p>
    <div class="slide-body">
      <div class="toolkit-grid">
        <div class="toolkit-card"><h4 class="en">Search</h4><ul><li>SerpAPI</li><li>Wikipedia</li><li>Tavily</li></ul></div>
        <div class="toolkit-card"><h4 class="en">Math & Code</h4><ul><li>LLMMathChain</li><li>Python REPL</li><li>Pandas</li></ul></div>
        <div class="toolkit-card"><h4 class="en">Web / API</h4><ul><li>Requests Toolkit</li><li>PlayWright</li></ul></div>
        <div class="toolkit-card"><h4 class="en">Productivity</h4><ul><li>Gmail</li><li>Google Calendar</li><li>Slack</li><li>GitHub</li></ul></div>
        <div class="toolkit-card"><h4 class="en">Files / Docs</h4><ul><li>FileSystem</li><li>Google Drive</li><li>VectorStoreQA</li></ul></div>
      </div>
      <div class="note-banner"><span class="en">Toolkit</span> = مجموعة أدوات مترابطة لغرض واحد (مثل <span class="en">SQL Database Toolkit</span>). ⚠️ بعض الأدوات مجانية وبعضها مدفوع — تحقق من التوثيق الرسمي دائمًا.</div>
    </div>
  </div>`
},

// ---------- 24. Structured Outputs ----------
{
  duration: 6,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Beyond Free Text</span>
    <h1 class="slide-title"><span class="en">Structured Outputs</span></h1>
    <p class="slide-desc">أحيانًا نريد من النموذج إخراجًا منظمًا (<span class="en">JSON</span>) وليس نصًا حرًا — للتخزين في قواعد بيانات، تكامل <span class="en">APIs</span>، أو <span class="en">workflows</span> متعددة الخطوات.</p>
    <div class="slide-body">
      <ul class="bullet-list">
        <li><span class="ico">📋</span><span class="en">Schema definition</span>: عبر <span class="en">JSON-like dict</span> أو <span class="en">Pydantic models</span> (<span class="en">type validation</span> + وثائق مدمجة).</li>
        <li><span class="ico">🔀</span>طريقتان: <span class="en">Tool calling</span> (ربط الـ <span class="en">schema</span> كأداة) أو <span class="en">JSON mode</span>.</li>
        <li><span class="ico">⚡</span><code class="en code">with_structured_output()</code>: الطريقة المختصرة في <span class="en">LangChain</span> — تربط الـ <span class="en">schema</span> وتفرض استخدامه وتعيد النتيجة <span class="en">parsed</span> جاهزة.</li>
      </ul>
      <div class="code-block" data-lang="python">
        <div class="code-block-head"><span class="code-dots"><i></i><i></i><i></i></span><span class="code-filename">example.py</span></div>
        <pre class="code-body"><code class="language-python">class Person(BaseModel):
    name: str
    interest: str

structured_llm = llm.with_structured_output(Person)
structured_llm.invoke("I'm Lance and I like to bike!")
# Person(name='Lance', interest='Biking')</code></pre>
      </div>
    </div>
  </div>`
},

// ---------- 25a. Stretch: Why RAG + Fine-tuning vs RAG ----------
{
  duration: 5,
  html: `
  <div class="slide-inner bonus-slide">
    <span class="bonus-badge">⭐ Stretch — RAG</span>
    <h1 class="slide-title">لماذا <span class="en">RAG؟</span> و<span class="en">Fine-tuning</span> مقابل <span class="en">RAG</span></h1>
    <p class="slide-desc">بيانات خاصة وحديثة غير موجودة في التدريب — بدل <span class="en">fine-tuning</span> مكلف، نمنح النموذج وثائق يبحث فيها وقت السؤال.</p>
    <div class="slide-body">
      <div class="compare-grid">
        <div class="compare-col neutral">
          <h3><span class="en">Fine-tuning</span></h3>
          <ul>
            <li>يغيّر <strong>سلوك</strong> النموذج أو <strong>أسلوبه</strong>.</li>
            <li>يحتاج بيانات تدريب وموارد حوسبة كبيرة.</li>
            <li>تحديث المعرفة يتطلب إعادة تدريب.</li>
          </ul>
        </div>
        <div class="compare-col highlight">
          <h3><span class="en">RAG</span></h3>
          <ul>
            <li>يضيف <strong>معرفة</strong> جديدة دون تعديل أوزان النموذج.</li>
            <li>تحديث المعرفة = تحديث الوثائق فقط.</li>
            <li>أرخص وأسرع للبدء، وقابل للتتبع (يمكن معرفة مصدر الإجابة).</li>
          </ul>
        </div>
      </div>
      <button type="button" class="skip-link" data-jump="quiz">⏭️ تخطّي إلى الـ Quiz (تخطي قسم Stretch)</button>
    </div>
  </div>`
},

// ---------- 25b. Stretch: Embeddings ----------
{
  duration: 4,
  html: `
  <div class="slide-inner bonus-slide">
    <span class="bonus-badge">⭐ Stretch — RAG</span>
    <h1 class="slide-title"><span class="en">Embeddings</span></h1>
    <div class="slide-body">
      <ul class="bullet-list">
        <li><span class="ico">🔢</span>تحويل النص إلى <span class="en">vectors</span> رقمية تلتقط المعنى.</li>
        <li><span class="ico">📍</span>النصوص المتشابهة معنويًا تكون متقاربة في الفضاء الرقمي (<span class="en">vector space</span>).</li>
      </ul>
      <div class="code-block" data-lang="python">
        <div class="code-block-head"><span class="code-dots"><i></i><i></i><i></i></span><span class="code-filename">example.py</span></div>
        <pre class="code-body"><code class="language-python">embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)
vector = embeddings.embed_query("What is Nebula's refund policy?")
# vector -> [0.021, -0.114, 0.087, ...]  (384 numbers)</code></pre>
      </div>
    </div>
  </div>`
},

// ---------- 25c. Stretch: Vector Databases ----------
{
  duration: 4,
  html: `
  <div class="slide-inner bonus-slide">
    <span class="bonus-badge">⭐ Stretch — RAG</span>
    <h1 class="slide-title"><span class="en">Vector Databases</span></h1>
    <div class="slide-body">
      <ul class="bullet-list">
        <li><span class="ico">💾</span>تخزين واسترجاع بالـ <span class="en">similarity search</span> بدل المطابقة الحرفية.</li>
        <li><span class="ico">🧭</span>عند سؤال جديد: نحوّله لـ <span class="en">vector</span> ونبحث عن أقرب النقاط المخزّنة.</li>
      </ul>
      <div class="cards-grid">
        <div class="card"><div class="card-icon">🎨</div><div class="card-title en">Chroma</div><div class="card-text">محلي وبسيط — مستخدم في <span class="en">Lab 4</span>.</div></div>
        <div class="card"><div class="card-icon">⚡</div><div class="card-title en">FAISS</div><div class="card-text">مكتبة <span class="en">Meta</span> السريعة للبحث المتجهي.</div></div>
        <div class="card"><div class="card-icon">🚀</div><div class="card-title en">Qdrant</div><div class="card-text">قاعدة <span class="en">vector DB</span> جاهزة للإنتاج، تعمل عبر <span class="en">Docker</span>.</div></div>
      </div>
    </div>
  </div>`
},

// ---------- 25d. Stretch: Full RAG pipeline ----------
{
  duration: 4,
  html: `
  <div class="slide-inner bonus-slide">
    <span class="bonus-badge">⭐ Stretch — RAG</span>
    <h1 class="slide-title">مسار <span class="en">RAG</span> الكامل</h1>
    <div class="slide-body">
      <div class="pipeline-flow">
        <div class="pipeline-box">Documents</div><div class="pipeline-arrow">→</div>
        <div class="pipeline-box">Chunking</div><div class="pipeline-arrow">→</div>
        <div class="pipeline-box">Embedding</div><div class="pipeline-arrow">→</div>
        <div class="pipeline-box accent">Vector DB</div><div class="pipeline-arrow">→</div>
        <div class="pipeline-box">Retrieval</div><div class="pipeline-arrow">→</div>
        <div class="pipeline-box">LLM + Context</div><div class="pipeline-arrow">→</div>
        <div class="pipeline-box accent">Answer</div>
      </div>
      <div class="note-banner">كل خطوة قابلة للاستبدال بشكل مستقل — نفس مبدأ <span class="en">Modularity</span> من الجلسة الأولى.</div>
    </div>
  </div>`
},

// ---------- 25e. Stretch: Lab 4 intro ----------
{
  duration: 3,
  html: `
  <div class="slide-inner bonus-slide">
    <span class="lab-badge">🧪 Lab 4 — Bonus</span>
    <h1 class="slide-title">مثال <span class="en">RAG</span> حقيقي</h1>
    <span class="lab-file">labs/04_rag_demo.py</span>
    <div class="slide-body">
      <ul class="bullet-list">
        <li><span class="ico">📄</span>ملف نصي محلي عن شركة وهمية (<code class="en code">labs/data/sample_doc.md</code>).</li>
        <li><span class="ico">✂️</span><span class="en">Chunking</span> → <span class="en">Embeddings</span> بنموذج مفتوح (<span class="en">sentence-transformers</span>) → <span class="en">Chroma</span> محلي.</li>
        <li><span class="ico">❓</span>سؤالان تجريبيان يثبتان أن الإجابة جاءت من الوثيقة نفسها وليس من معرفة النموذج المسبقة.</li>
      </ul>
    </div>
  </div>`
},

// ---------- 26. Quiz CTA ----------
{
  duration: 2,
  html: `
  <div class="slide-inner quiz-cta">
    <span class="slide-eyebrow">Quick Check</span>
    <h1 class="slide-title"><span class="en">Quiz</span> الجلسة</h1>
    <p class="slide-desc" style="text-align:center;">يغطي: دورة حياة <span class="en">Tool Call</span>، طرق إنشاء الأدوات، <span class="en">Manual Tool Calling</span>، <span class="en">Structured Outputs</span>.</p>
    <div class="qr-placeholder">QR&nbsp;Code</div>
    <a class="quiz-button" href="QUIZ_URL_HERE" target="_blank" rel="noopener">🚀 ابدأ الـ Quiz</a>
    <span class="quiz-hint">// عدّل الرابط في slides.js — ابحث عن "QUIZ_URL_HERE"</span>
  </div>`
},

// ---------- 27. Next session teaser ----------
{
  duration: 2,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Next Up</span>
    <h1 class="slide-title">الجلسة القادمة: <span class="en">LangGraph & Multi-Agents</span></h1>
    <p class="slide-desc">ستكون عملية أيضًا.</p>
    <div class="slide-body">
      <ul class="bullet-list">
        <li><span class="ico">🕸️</span>بناء <span class="en">Agents</span> بتحكم أدق عبر <span class="en">LangGraph</span> (<span class="en">orchestration</span> منخفض المستوى، <code class="en code">create_react_agent</code>).</li>
        <li><span class="ico">🤝</span>أنظمة <span class="en">Multi-Agent</span>: عدة وكلاء يتعاونون على مهمة واحدة.</li>
      </ul>
    </div>
  </div>`
},

// ---------- 28. References ----------
{
  duration: 1,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">References</span>
    <h1 class="slide-title">المراجع <span class="en">(References)</span></h1>
    <div class="slide-body">
      <div class="reference-list">
        <a class="reference-item" href="REFERENCE_URL_HERE" target="_blank" rel="noopener">
          <span class="ref-ico">🎓</span>
          <span class="ref-body"><span class="ref-title en">IBM — "AI agents and Agentic AI workflows"</span><span class="ref-sub">Coursera course</span></span>
          <span class="ref-go">↗</span>
        </a>
        <a class="reference-item" href="https://python.langchain.com/docs/concepts/tools/" target="_blank" rel="noopener">
          <span class="ref-ico">🦜</span>
          <span class="ref-body"><span class="ref-title en">LangChain Tools documentation</span><span class="ref-sub">python.langchain.com</span></span>
          <span class="ref-go">↗</span>
        </a>
        <a class="reference-item" href="https://python.langchain.com/docs/concepts/tool_calling/" target="_blank" rel="noopener">
          <span class="ref-ico">🔧</span>
          <span class="ref-body"><span class="ref-title en">LangChain Tool Calling</span><span class="ref-sub">python.langchain.com</span></span>
          <span class="ref-go">↗</span>
        </a>
        <a class="reference-item" href="https://python.langchain.com/docs/concepts/structured_outputs/" target="_blank" rel="noopener">
          <span class="ref-ico">📋</span>
          <span class="ref-body"><span class="ref-title en">Structured Outputs</span><span class="ref-sub">python.langchain.com</span></span>
          <span class="ref-go">↗</span>
        </a>
        <a class="reference-item" href="https://ollama.com" target="_blank" rel="noopener">
          <span class="ref-ico">🦙</span>
          <span class="ref-body"><span class="ref-title en">Ollama</span><span class="ref-sub">ollama.com</span></span>
          <span class="ref-go">↗</span>
        </a>
        <a class="reference-item" href="https://huggingface.co/docs/api-inference" target="_blank" rel="noopener">
          <span class="ref-ico">🤗</span>
          <span class="ref-body"><span class="ref-title en">HuggingFace Inference</span><span class="ref-sub">huggingface.co/docs/api-inference</span></span>
          <span class="ref-go">↗</span>
        </a>
        <a class="reference-item" href="https://docs.trychroma.com" target="_blank" rel="noopener">
          <span class="ref-ico">🎨</span>
          <span class="ref-body"><span class="ref-title en">Chroma (للـ RAG bonus)</span><span class="ref-sub">docs.trychroma.com</span></span>
          <span class="ref-go">↗</span>
        </a>
      </div>
    </div>
  </div>`
},

// ---------- 29. Thank you ----------
{
  duration: null,
  durationText: "ختام",
  html: `
  <div class="slide-inner thanks-slide">
    <div class="thanks-emoji">🙏</div>
    <h1 class="slide-title">شكرًا لك!</h1>
    <p class="slide-desc" style="text-align:center;">نهاية الجلسة الثانية — نراكم في الجلسة القادمة: <span class="en">LangGraph & Multi-Agents</span>.</p>
    <div class="contact-fields">
      <span class="contact-field">📅 [أضف موعد الجلسة القادمة هنا]</span>
      <span class="contact-field">✉️ [أضف بريدك الإلكتروني هنا]</span>
      <span class="contact-field">💬 [أضف رابط التواصل / المجتمع هنا]</span>
    </div>
  </div>`
},

];
