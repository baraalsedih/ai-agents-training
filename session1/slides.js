/* =========================================================
   SLIDES DATA
   -----------------------------------------------------------
   Each slide = { duration, durationText, html }
     - duration:      minutes (Number) used by the presenter timer.
                       Leave as `null` if the slide has no timer
                       (e.g. shares time with the previous slide).
     - durationText:  optional override string for the time badge
                       (e.g. "ضمن نفس الوقت"). If omitted, the badge
                       is generated automatically from `duration`.
     - html:          the slide's inner markup. Wrap the whole thing
                       in <div class="slide-inner">...</div>.
   To add / edit a slide: just add / edit an object in this array —
   script.js re-renders everything automatically, no other file
   needs to change.
========================================================= */

const SLIDES = [

// ---------- 1. Title ----------
{
  duration: 2,
  html: `
  <div class="slide-inner title-slide">
    <span class="eyebrow en">AI Agents Course</span>
    <h1 class="slide-title">الجلسة الأولى</h1>
    <h2 class="slide-subtitle en">AI Systems, Workflows, and Agents</h2>
    <p class="slide-desc">فهم أنواع الأنظمة، وكيفية اختيار النظام والأدوات المناسبة لمشكلتك.</p>
    <div class="title-meta">
      <div class="meta-pill">⏱️ مدة الجلسة: ساعتان</div>
      <div class="meta-pill">📚 Based on IBM <span class="en">"AI agents and Agentic AI workflows"</span> — Coursera</div>
    </div>
  </div>`
},

// ---------- 2. Objectives ----------
{
  duration: 3,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Session Objectives</span>
    <h1 class="slide-title">أهداف الجلسة</h1>
    <div class="slide-body">
      <ul class="bullet-list">
        <li><span class="num">1</span>التمييز بين <span class="en">Single LLM</span> و<span class="en">Workflow</span> و<span class="en">AI Agent</span>.</li>
        <li><span class="num">2</span>فهم لماذا تحوّلت الأنظمة من <span class="en">Monolith</span> إلى <span class="en">Compound Systems</span>.</li>
        <li><span class="num">3</span>فهم مبدأ <span class="en">Control Logic</span>: البرمجي (<span class="en">Programmatic</span>) مقابل الوكيلي (<span class="en">Agentic</span>).</li>
        <li><span class="num">4</span>التعرّف على نمط <span class="en">ReAct (Reason + Act)</span>.</li>
        <li><span class="num">5</span>معرفة متى تُستخدم كل نوع نظام بناءً على معايير واضحة.</li>
      </ul>
    </div>
  </div>`
},

// ---------- 3. Agenda / timeline ----------
{
  duration: 3,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Agenda</span>
    <h1 class="slide-title">خطة الجلسة والتوقيت</h1>
    <div class="slide-body">
      <div class="timeline-wrap">
        <span class="timeline-total">الإجمالي التقريبي: ١٠٠ دقيقة من أصل ١٢٠ دقيقة</span>
        <ul class="timeline-list">
          <li class="timeline-item"><span class="timeline-topic">من <span class="en">Monolith</span> إلى <span class="en">Compound Systems</span></span><span class="timeline-time">10′</span></li>
          <li class="timeline-item"><span class="timeline-topic">مشكلة المعرفة المحدودة (<span class="en">Limited Knowledge</span>)</span><span class="timeline-time">8′</span></li>
          <li class="timeline-item"><span class="timeline-topic"><span class="en">System Design</span> principles و<span class="en">Modularity</span></span><span class="timeline-time">8′</span></li>
          <li class="timeline-item"><span class="timeline-topic"><span class="en">Control Logic</span>: <span class="en">Programmatic</span> مقابل <span class="en">Agentic</span></span><span class="timeline-time">10′</span></li>
          <li class="timeline-item"><span class="timeline-topic"><span class="en">Think Fast or Think Slow</span></span><span class="timeline-time">5′</span></li>
          <li class="timeline-item"><span class="timeline-topic">ما الذي يجعل النظام <span class="en">Agent</span></span><span class="timeline-time">8′</span></li>
          <li class="timeline-item"><span class="timeline-topic">نمط <span class="en">ReAct</span> ومثال تطبيقي</span><span class="timeline-time">14′</span></li>
          <li class="timeline-item"><span class="timeline-topic">مقارنة <span class="en">Single LLM</span> و<span class="en">Workflow</span> و<span class="en">Agent</span></span><span class="timeline-time">8′</span></li>
          <li class="timeline-item"><span class="timeline-topic">إطار القرار الرباعي (<span class="en">Four-Criteria Framework</span>)</span><span class="timeline-time">10′</span></li>
          <li class="timeline-item"><span class="timeline-topic">متى لا تُستخدم <span class="en">Agents</span> وإدارة المخاطر</span><span class="timeline-time">12′</span></li>
          <li class="timeline-item"><span class="timeline-topic"><span class="en">Quiz</span> والجلسة القادمة والمراجع</span><span class="timeline-time">7′</span></li>
        </ul>
      </div>
    </div>
  </div>`
},

// ---------- 4. Why move away from Monolith ----------
{
  duration: 10,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">From Monolith to Compound</span>
    <h1 class="slide-title">لماذا نبتعد عن الأنظمة الأحادية <span class="en">(Monolith AI Systems)</span>؟</h1>
    <p class="slide-desc">العالم ينتقل من الاعتماد على نموذج واحد (<span class="en">fine-tuned LLM</span>) إلى <span class="en">Compound Systems</span> للأسباب التالية:</p>
    <div class="slide-body">
      <div class="cards-grid">
        <div class="card">
          <div class="card-icon">🧩</div>
          <div class="card-title"><span class="en">Hard to Adapt</span></div>
          <div class="card-text">صعوبة التكيف مع مشاكل جديدة أو متغيرة دون إعادة تدريب النموذج بالكامل.</div>
        </div>
        <div class="card">
          <div class="card-icon">📚</div>
          <div class="card-title"><span class="en">Limited Knowledge</span></div>
          <div class="card-text">معرفة محدودة بما هو خارج بيانات التدريب أو الـ <span class="en">prompt</span>.</div>
        </div>
        <div class="card">
          <div class="card-icon">🔗</div>
          <div class="card-title">مرونة أكبر</div>
          <div class="card-text">الحاجة لأنظمة تجمع بين عدة مكونات <span class="en">specialized</span> بدل الاعتماد على مكوّن واحد.</div>
        </div>
      </div>
    </div>
  </div>`
},

// ---------- 5. Limited Knowledge diagram ----------
{
  duration: null,
  durationText: "ضمن نفس الوقت",
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">The Problem</span>
    <h1 class="slide-title">مشكلة المعرفة المحدودة <span class="en">(Limited Knowledge)</span></h1>
    <div class="slide-body">
      <div class="flow-diagram">
        <div class="flow-box">Query</div>
        <div class="flow-arrow">→</div>
        <div class="flow-box accent">LLM</div>
        <div class="flow-arrow">→</div>
        <div class="flow-box">Response</div>
      </div>
      <ul class="bullet-list">
        <li><span class="ico">⚙️</span>كيف يعمل الـ <span class="en">LLM</span> العادي: الـ <span class="en">Query</span> يدخل مباشرة إلى الـ <span class="en">LLM</span>.</li>
        <li><span class="ico">🎲</span>يتم توليد الـ <span class="en">Response</span> بناءً على <span class="en">similarity</span> فقط، وليس معرفة حقيقية.</li>
        <li><span class="ico">❗</span>المشكلة: النموذج لا يعرف شيئًا عنك لم يُذكر داخل الـ <span class="en">prompt</span>.</li>
      </ul>
    </div>
  </div>`
},

// ---------- 6. Agent solves it - weather example ----------
{
  duration: 8,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Example</span>
    <h1 class="slide-title">كيف يحل <span class="en">AI Agent</span> هذه المشكلة؟ — مثال الطقس</h1>
    <div class="slide-body">
      <div class="compare-grid">
        <div class="compare-col neutral">
          <h3>LLM عادي</h3>
          <ul>
            <li>يستقبل السؤال "كيف الطقس اليوم؟" بدون أي سياق إضافي.</li>
            <li>لا يعرف موقعك ولا يملك بيانات حيّة عن الطقس.</li>
            <li>يعطي إجابة عامة أو تخمينية غير دقيقة.</li>
          </ul>
        </div>
        <div class="compare-col highlight">
          <h3><span class="en">AI Agent</span></h3>
          <ul>
            <li>يحلّل الـ <span class="en">query</span> ويحدد التفاصيل الإضافية المطلوبة (مثل موقعي).</li>
            <li>يبحث عن بيانات إضافية (حالة الطقس في بلدي من قاعدة بيانات).</li>
            <li>يجمع النتائج معًا ليعطي إجابة صحيحة ومخصصة.</li>
          </ul>
        </div>
      </div>
      <div class="note-banner">الخلاصة: إجابة الـ <span class="en">Agent</span> مبنية على مصادر حقيقية وليست تخمين نصي فقط.</div>
    </div>
  </div>`
},

// ---------- 7. System Design & Modularity ----------
{
  duration: 8,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Foundations</span>
    <h1 class="slide-title">مبادئ <span class="en">System Design</span> و<span class="en">Modularity</span></h1>
    <p class="slide-desc">لبناء <span class="en">Compound System</span> بطريقة صحيحة نحتاج مبادئ <span class="en">System Design</span> — كل نظام جيد مبني من مكونات <span class="en">modular</span> متعددة.</p>
    <div class="slide-body">
      <div class="cards-grid">
        <div class="card">
          <div class="card-icon">🧠</div>
          <div class="card-title en">LLM</div>
          <div class="card-text">المكوّن المسؤول عن الفهم، التوليد، والتفكير اللغوي.</div>
        </div>
        <div class="card">
          <div class="card-icon">🗄️</div>
          <div class="card-title en">Database</div>
          <div class="card-text">مصدر بيانات حقيقي ومحدّث يُغني إجابات النظام.</div>
        </div>
        <div class="card">
          <div class="card-icon">✅</div>
          <div class="card-title en">Output Verifier</div>
          <div class="card-text">مكوّن يتحقق من صحة وسلامة المخرجات قبل تسليمها.</div>
        </div>
      </div>
      <div class="note-banner">عند بناء <span class="en">Compound AI System</span> نحصل على نظام <span class="en">Modular</span> وسهل التكيف (<span class="en">Easy to Adapt</span>) — كل مكوّن يمكن تطويره واستبداله بشكل مستقل.</div>
    </div>
  </div>`
},

// ---------- 8. Control Logic ----------
{
  duration: 10,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Control Logic</span>
    <h1 class="slide-title"><span class="en">Control Logic</span>: البرمجي مقابل الوكيلي</h1>
    <p class="slide-desc">نوعان رئيسيان للتحكّم في تدفّق النظام:</p>
    <div class="slide-body">
      <div class="logic-grid">
        <div class="logic-box programmatic">
          <h3><span class="en">Programmatic</span> Control Logic</h3>
          <p>الإنسان يتحكم في منطق تدفق العملية خطوة بخطوة — كل مسار محدد مسبقًا في الكود.</p>
        </div>
        <div class="logic-box agentic">
          <h3><span class="en">Agentic</span> Control Logic</h3>
          <p>نضع الـ <span class="en">LLM</span> في موقع القيادة؛ نغذّيه بمشكلة معقدة فيقوم بتقسيمها إلى مهام أصغر (<span class="en">Divide and Conquer</span>).</p>
        </div>
      </div>
      <div class="note-banner">هنا بالضبط يظهر مفهوم الـ <span class="en">Agent</span>.</div>
    </div>
  </div>`
},

// ---------- 9. Think Fast / Think Slow ----------
{
  duration: 5,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Cognitive Modes</span>
    <h1 class="slide-title"><span class="en">Think Fast or Think Slow</span></h1>
    <p class="slide-desc">أحيانًا نحتاج النظام يفكر بسرعة، وأحيانًا يفكر ببطء وعمق.</p>
    <div class="slide-body">
      <div class="think-grid">
        <div class="think-col fast">
          <div class="think-icon">⚡</div>
          <h3><span class="en">Think Fast</span></h3>
          <p>قرارات سريعة لمهام بسيطة ومباشرة، تشبه <span class="en">Single LLM call</span>.</p>
        </div>
        <div class="think-col slow">
          <div class="think-icon">🐢</div>
          <h3><span class="en">Think Slow</span></h3>
          <p>تفكير تدريجي ومتعمق للمهام المعقدة، يشبه <span class="en">Agent loop</span>.</p>
        </div>
      </div>
      <p class="slide-desc" style="margin:0 auto;text-align:center;">اختيار النمط المناسب يعتمد على طبيعة المشكلة والوقت المتاح.</p>
    </div>
  </div>`
},

// ---------- 10. What makes a system an Agent ----------
{
  duration: 8,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Anatomy of an Agent</span>
    <h1 class="slide-title">ما الذي يجعل النظام <span class="en">AI Agent</span>؟</h1>
    <div class="slide-body">
      <div class="cards-grid">
        <div class="card">
          <div class="card-icon">🧠</div>
          <div class="card-title en">Reason</div>
          <div class="card-text">القدرة على التفكير والتخطيط لحل المشكلة.</div>
        </div>
        <div class="card">
          <div class="card-icon">🛠️</div>
          <div class="card-title en">Act (via Tools)</div>
          <div class="card-text">التنفيذ عبر أدوات مثل <span class="en">Search</span> أو <span class="en">Calculator</span> أو <span class="en">LLM</span> آخر (مثل <span class="en">Translator</span>).</div>
        </div>
        <div class="card">
          <div class="card-icon">💾</div>
          <div class="card-title en">Access Memory</div>
          <div class="card-text">تذكّر السياق طوال الجلسة (<span class="en">Session Context</span>).</div>
        </div>
      </div>
      <div class="note-banner">توفّر هذه العناصر الثلاثة معًا هو ما يميّز الـ <span class="en">Agent</span> عن أي نظام آخر.</div>
    </div>
  </div>`
},

// ---------- 11. ReAct pattern ----------
{
  duration: 8,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">The Pattern</span>
    <h1 class="slide-title">نمط <span class="en">ReAct</span></h1>
    <p class="slide-desc">أحد أشهر الطرق لدمج مكونات الـ <span class="en">Agent</span> هو نمط <span class="en">ReAct</span>.</p>
    <div class="slide-body">
      <div class="react-loop-wrap">
        <div class="react-loop">
          <div class="react-loop-circle"></div>
          <div class="react-center"><span class="rc-title">ReAct</span><span class="rc-sub">loop</span></div>
          <div class="react-node n-top">Query</div>
          <div class="react-node n-right">Plan <span class="hint">/ Think</span></div>
          <div class="react-node n-bottom">Act <span class="hint">(Tools)</span></div>
          <div class="react-node n-left">Observe</div>
          <div class="react-loop-arrow arrow-tr">↘</div>
          <div class="react-loop-arrow arrow-br">↙</div>
          <div class="react-loop-arrow arrow-bl">↖</div>
          <div class="react-loop-arrow arrow-tl">↗</div>
        </div>
        <p class="react-note">في مرحلة <span class="en">Observe</span> يقرر النظام: هل يجيب المستخدم مباشرة (<span class="en">Answer</span>)، أم يعود لمرحلة التفكير (<span class="en">Plan / Think</span>) من جديد؟</p>
        <div class="reference-chip">📄 <span class="en">Reference: "ReAct: Synergizing Reasoning and Acting in Language Models"</span> — arXiv</div>
      </div>
    </div>
  </div>`
},

// ---------- 12. Applied example: what to wear ----------
{
  duration: 6,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Applied Example</span>
    <h1 class="slide-title">مثال تطبيقي: <span class="en">"ماذا ألبس اليوم؟"</span></h1>
    <div class="slide-body">
      <div class="stepper">
        <div class="step">
          <div class="step-index">1</div>
          <div class="step-content">
            <h4><span class="en">Plan</span></h4>
            <p>النظام يدرك أنه يحتاج: الموقع، درجة الحرارة، تفضيلات المستخدم، والعمر.</p>
          </div>
        </div>
        <div class="step">
          <div class="step-index">2</div>
          <div class="step-content">
            <h4><span class="en">Act</span></h4>
            <p>يبحث عن هذه البيانات (<span class="en">Search</span>).</p>
          </div>
        </div>
        <div class="step">
          <div class="step-index">3</div>
          <div class="step-content">
            <h4><span class="en">Observe</span></h4>
            <p>يتحقق هل المعلومات كافية للإجابة.</p>
          </div>
        </div>
        <div class="step final">
          <div class="step-index">4</div>
          <div class="step-content">
            <h4><span class="en">Answer</span></h4>
            <p>يقدّم توصية اللباس المناسبة بناءً على البيانات المجمّعة.</p>
          </div>
        </div>
      </div>
    </div>
  </div>`
},

// ---------- 13. Comparison table ----------
{
  duration: 8,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Comparison</span>
    <h1 class="slide-title">مقارنة الأنظمة: <span class="en">Single LLM / Workflow / Agent</span></h1>
    <div class="slide-body">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr><th>النوع</th><th>العملية</th><th>حالة الاستخدام</th><th>مزايا</th><th>عيوب</th></tr>
          </thead>
          <tbody>
            <tr>
              <td><strong class="en">Single LLM</strong></td>
              <td class="proc">Input → LLM → Output</td>
              <td><span class="en">Summarization</span>، <span class="en">Classification</span></td>
              <td>بسيط وسريع ورخيص</td>
              <td>غير قابل للتكيف، يفتقر للسياق</td>
            </tr>
            <tr>
              <td><strong class="en">Workflow</strong></td>
              <td class="proc">Parallel LLMs → Aggregation → Output</td>
              <td>مهام متعددة الخطوات</td>
              <td>يمكن التنبؤ به، سهل المراجعة</td>
              <td>جامد وغير ديناميكي</td>
            </tr>
            <tr>
              <td><strong class="en">Agent</strong></td>
              <td class="proc">Plan → Act → Observe (loop)</td>
              <td>أتمتة معقدة ومتكيفة</td>
              <td>مرن ويتعلم من الملاحظات</td>
              <td>غير متوقع، معقّد، وأغلى تكلفة</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>`
},

// ---------- 14. Four-criteria framework ----------
{
  duration: 10,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Decision Framework</span>
    <h1 class="slide-title">إطار القرار الرباعي <span class="en">(Four-Criteria Framework)</span></h1>
    <div class="slide-body">
      <div class="framework-grid">
        <div class="framework-card">
          <div class="framework-number">1</div>
          <div>
            <h4>هل المهمة <span class="en">Ambiguous</span> أم <span class="en">Predictable</span>؟</h4>
            <p>استخدم <span class="en">Agent</span> للمهام الغامضة، و<span class="en">Workflow</span> للمهام الواضحة.</p>
          </div>
        </div>
        <div class="framework-card">
          <div class="framework-number">2</div>
          <div>
            <h4>هل قيمة المهمة تستحق التكلفة؟</h4>
            <p>الـ <span class="en">Agent</span> يستهلك من 10 إلى 100 ضعف عدد الـ <span class="en">tokens</span> مقارنة بـ <span class="en">Workflow</span>.</p>
          </div>
        </div>
        <div class="framework-card">
          <div class="framework-number">3</div>
          <div>
            <h4>هل يحقق الـ <span class="en">Agent</span> الحد الأدنى من القدرات؟</h4>
            <p>اختبره على 3 إلى 5 مهارات أساسية قبل الإطلاق.</p>
          </div>
        </div>
        <div class="framework-card">
          <div class="framework-number">4</div>
          <div>
            <h4>ماذا يحدث إذا أخطأ الـ <span class="en">Agent</span>؟</h4>
            <p>هل يمكن اكتشاف الخطأ وتصحيحه بسرعة؟ وما مستوى خطورته؟</p>
          </div>
        </div>
      </div>
    </div>
  </div>`
},

// ---------- 15. When NOT to use agents ----------
{
  duration: 6,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Boundaries</span>
    <h1 class="slide-title">متى لا تستخدم <span class="en">AI Agents</span>؟</h1>
    <div class="slide-body">
      <ul class="bullet-list warning">
        <li><span class="ico">🚫</span>المهام عالية الحجم ومنخفضة الهامش، مثل <span class="en">Basic Chat Support</span>.</li>
        <li><span class="ico">⏱️</span>التطبيقات الفورية (<span class="en">Real-Time Applications</span>) مثل كشف الاحتيال اللحظي.</li>
        <li><span class="ico">🛑</span>الأنظمة صفرية الخطأ (<span class="en">Zero-Error Systems</span>) كالقرارات الطبية أو الأمنية.</li>
        <li><span class="ico">📏</span>الصناعات شديدة التنظيم التي تتطلب نتائج <span class="en">Deterministic</span>.</li>
      </ul>
    </div>
  </div>`
},

// ---------- 16. Risk management / human in the loop ----------
{
  duration: 6,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Risk Management</span>
    <h1 class="slide-title">إدارة المخاطر و<span class="en">Human in the Loop</span></h1>
    <div class="slide-body">
      <div class="risk-grid">
        <div class="risk-box">
          <div class="risk-icon">🌐</div>
          <h4 class="en">Environment</h4>
          <p>البيئة الرقمية التي يعمل بها الـ <span class="en">Agent</span>.</p>
        </div>
        <div class="risk-box">
          <div class="risk-icon">🛠️</div>
          <h4 class="en">Tools</h4>
          <p>الواجهات التي يستخدمها للتصرف أو الملاحظة.</p>
        </div>
        <div class="risk-box">
          <div class="risk-icon">📜</div>
          <h4 class="en">System Prompts</h4>
          <p>القواعد والأهداف والسلوكيات الموجّهة.</p>
        </div>
      </div>
      <ul class="checklist">
        <li><span class="ico">✔</span>ابدأ بصلاحيات <span class="en">Read-Only</span>.</li>
        <li><span class="ico">✔</span>أضف موافقة بشرية للخطوات الحرجة.</li>
        <li><span class="ico">✔</span>استخدم <span class="en">Staged Deployment</span> مع <span class="en">Monitoring</span> و<span class="en">Logging</span> شامل.</li>
      </ul>
    </div>
  </div>`
},

// ---------- 17. Quiz CTA ----------
{
  duration: 2,
  html: `
  <div class="slide-inner quiz-cta">
    <span class="slide-eyebrow">Quick Check</span>
    <h1 class="slide-title"><span class="en">Quiz</span> الجلسة</h1>
    <p class="slide-desc" style="text-align:center;">يستغرق حوالي 5 دقائق ويغطي المفاهيم الأساسية: <span class="en">Single LLM</span>، <span class="en">Workflow</span>، <span class="en">Agent</span>، و<span class="en">ReAct</span>.</p>
    <div class="qr-placeholder">QR&nbsp;Code</div>
    <a class="quiz-button" href="QUIZ_URL_HERE" target="_blank" rel="noopener">🚀 ابدأ الـ Quiz</a>
    <span class="quiz-hint">// عدّل الرابط في slides.js — ابحث عن "QUIZ_URL_HERE"</span>
  </div>`
},

// ---------- 18. Next session teaser ----------
{
  duration: 3,
  html: `
  <div class="slide-inner">
    <span class="slide-eyebrow">Next Up</span>
    <h1 class="slide-title">الجلسة القادمة: <span class="en">Tool Calling and Chaining</span></h1>
    <p class="slide-desc">نظرة سريعة على موضوع الجلسة الثانية، وستكون عملية (<span class="en">Practical</span>).</p>
    <div class="slide-body">
      <ul class="bullet-list">
        <li><span class="ico">🛠️</span>كيف ولماذا تستخدم الـ <span class="en">Agents</span> الأدوات (<span class="en">Tools</span>).</li>
        <li><span class="ico">🧱</span>كيفية إنشاء <span class="en">Tool</span> باستخدام <span class="en">LangChain</span>.</li>
        <li><span class="ico">🔀</span>أشهر أنواع <span class="en">Tool Calling</span> المستخدمة في المشاريع الحقيقية.</li>
      </ul>
    </div>
  </div>`
},

// ---------- 19. References ----------
{
  duration: 2,
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
        <a class="reference-item" href="REFERENCE_URL_HERE" target="_blank" rel="noopener">
          <span class="ref-ico">📄</span>
          <span class="ref-body"><span class="ref-title en">ReAct: Synergizing Reasoning and Acting in Language Models</span><span class="ref-sub">research paper — arXiv</span></span>
          <span class="ref-go">↗</span>
        </a>
        <a class="reference-item" href="REFERENCE_URL_HERE" target="_blank" rel="noopener">
          <span class="ref-ico">🔌</span>
          <span class="ref-body"><span class="ref-title en">Model Context Protocol (MCP)</span><span class="ref-sub">by Anthropic — documentation</span></span>
          <span class="ref-go">↗</span>
        </a>
        <a class="reference-item" href="REFERENCE_URL_HERE" target="_blank" rel="noopener">
          <span class="ref-ico">🔗</span>
          <span class="ref-body"><span class="ref-title en">Agent Communication Protocol (ACP)</span><span class="ref-sub">by IBM — documentation</span></span>
          <span class="ref-go">↗</span>
        </a>
        <a class="reference-item" href="https://docs.langchain.com" target="_blank" rel="noopener">
          <span class="ref-ico">🦜</span>
          <span class="ref-body"><span class="ref-title en">LangChain documentation</span><span class="ref-sub">للجلسة القادمة — docs.langchain.com</span></span>
          <span class="ref-go">↗</span>
        </a>
      </div>
    </div>
  </div>`
},

// ---------- 20. Thank you ----------
{
  duration: null,
  durationText: "ختام",
  html: `
  <div class="slide-inner thanks-slide">
    <div class="thanks-emoji">🙏</div>
    <h1 class="slide-title">شكرًا لك!</h1>
    <p class="slide-desc" style="text-align:center;">نهاية الجلسة الأولى — نراكم في الجلسة القادمة: <span class="en">Tool Calling and Chaining</span>.</p>
    <div class="contact-fields">
      <span class="contact-field">📅 [أضف موعد الجلسة القادمة هنا]</span>
      <span class="contact-field">✉️ [أضف بريدك الإلكتروني هنا]</span>
      <span class="contact-field">💬 [أضف رابط التواصل / المجتمع هنا]</span>
    </div>
  </div>`
},

];
