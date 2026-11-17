// NEETFlow Frontend Logic
let currentTimeline = null;
let currentDay = 1;
let allChapters = [];
let testTimer = null;
let timerSeconds = 15 * 60;

document.addEventListener("DOMContentLoaded", () => {
  // Set default start date to today in modals
  const todayStr = new Date().toISOString().split("T")[0];
  const dateInput = document.getElementById("input-start-date");
  if (dateInput) dateInput.value = todayStr;
  const logDateInput = document.getElementById("log-date");
  if (logDateInput) logDateInput.value = todayStr;

  initApp();
});

async function initApp() {
  await fetchTimeline();
  await loadChapters();
  await loadHourGuide(10.0);
}

// Tab Switching
function switchTab(tabId) {
  document.querySelectorAll(".nav-tab").forEach(btn => {
    btn.classList.remove("active");
    btn.classList.add("text-slate-400");
  });
  document.querySelectorAll(".tab-view").forEach(view => {
    view.classList.add("hidden");
    view.classList.remove("block");
  });

  const activeBtn = document.getElementById(`tab-${tabId}`);
  if (activeBtn) {
    activeBtn.classList.add("active");
    activeBtn.classList.remove("text-slate-400");
  }

  const activeView = document.getElementById(`view-${tabId}`);
  if (activeView) {
    activeView.classList.remove("hidden");
    activeView.classList.add("block");
  }

  if (tabId === "test-arena") {
    loadTestQuestions();
  } else if (tabId === "mistakes") {
    loadMistakes();
  } else if (tabId === "syllabus") {
    renderSyllabusGrid();
  }
}

// Fetch Active Timeline
async function fetchTimeline() {
  try {
    const res = await fetch("/api/timeline");
    const data = await res.json();
    if (data.timeline) {
      currentTimeline = data.timeline;
      updateHeroStats(data.timeline, data.stats);
      document.getElementById("btn-timeline-text").textContent = "Re-Generate Plan";
      loadDayTasks(currentDay);
    } else {
      // Prompt user or auto-generate default 6-month timeline
      document.getElementById("hero-timeline-name").textContent = "No Timeline Configured";
      document.getElementById("hero-title").textContent = "Ready to start your 6-month journey?";
      document.getElementById("btn-timeline-text").textContent = "Generate 6-Month Plan";
      openTimelineModal();
    }
  } catch (err) {
    console.error("Failed to load timeline:", err);
  }
}

function updateHeroStats(timeline, stats) {
  document.getElementById("hero-timeline-name").textContent = timeline.name;
  document.getElementById("hero-title").textContent = `${timeline.total_days}-Day NEET Preparation Mission`;
  document.getElementById("stat-total-days").textContent = `${timeline.total_days} Days`;
  document.getElementById("stat-daily-hours").textContent = `${timeline.daily_hours} hrs / day`;
  
  const jumpInput = document.getElementById("input-jump-day");
  if (jumpInput) jumpInput.max = timeline.total_days;

  if (stats) {
    document.getElementById("stat-progress-tasks").textContent = `${stats.completed_tasks || 0} / ${stats.total_tasks || 0}`;
    document.getElementById("stat-progress-hours").textContent = `${(stats.completed_hours || 0).toFixed(1)} hrs`;
  }
}

// Load tasks for current day
async function loadDayTasks(day) {
  if (!currentTimeline) return;
  const container = document.getElementById("daily-tasks-container");
  container.innerHTML = `<div class="p-8 text-center text-slate-500">Loading Day ${day} tasks...</div>`;

  document.getElementById("current-day-label").textContent = `Day ${day} of ${currentTimeline.total_days}`;
  document.getElementById("input-jump-day").value = day;

  try {
    const res = await fetch(`/api/tasks?timeline_id=${currentTimeline.id}&day=${day}`);
    const tasks = await res.json();

    if (!tasks || tasks.length === 0) {
      container.innerHTML = `
        <div class="p-8 rounded-xl bg-slate-900 border border-slate-800 text-center text-slate-400">
          <p class="text-base font-semibold">No tasks scheduled for Day ${day}.</p>
          <p class="text-xs text-slate-500 mt-1">Use this buffer day for resting or revising your Mistake Notebook.</p>
        </div>
      `;
      return;
    }

    document.getElementById("current-date-label").textContent = `Scheduled: ${tasks[0].scheduled_date}`;

    container.innerHTML = tasks.map(task => {
      const isCompleted = task.status === "COMPLETED";
      const subjectBadgeColor = getSubjectColorClass(task.subject);
      const isRevision = task.task_type.startsWith("REVISION");
      const isMock = task.task_type === "MOCK_TEST";

      let typeBadge = "";
      if (isRevision) {
        typeBadge = `<span class="text-xs px-2 py-0.5 rounded-full bg-pink-500/15 text-pink-400 border border-pink-500/30">Spaced Revision</span>`;
      } else if (isMock) {
        typeBadge = `<span class="text-xs px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-400 border border-purple-500/30">NEET Mock Test</span>`;
      } else {
        typeBadge = `<span class="text-xs px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-400 border border-indigo-500/30">Core Study</span>`;
      }

      let weightageBadge = "";
      if (task.weightage === "High") {
        weightageBadge = `<span class="text-xs px-2 py-0.5 rounded-full bg-rose-500/15 text-rose-400 border border-rose-500/30 font-semibold">🔥 High Weightage (~${task.avg_questions || 3} Qs/yr)</span>`;
      } else if (task.weightage === "Medium") {
        weightageBadge = `<span class="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">Medium Weightage (~${task.avg_questions || 2} Qs/yr)</span>`;
      }

      return `
        <div class="p-4 sm:p-5 rounded-xl border transition-all ${isCompleted ? 'bg-slate-950/40 border-slate-800/50 opacity-70' : 'bg-slate-900 border-slate-800 hover:border-slate-700 shadow-lg'} flex items-start sm:items-center justify-between gap-4">
          <div class="flex items-start sm:items-center gap-4">
            <input type="checkbox" ${isCompleted ? 'checked' : ''} onchange="toggleTask(${task.id}, this.checked)" class="task-checkbox mt-1 sm:mt-0 w-5 h-5 rounded cursor-pointer accent-emerald-500" />
            <div>
              <div class="flex flex-wrap items-center gap-2 mb-1">
                <span class="text-xs font-bold uppercase tracking-wider ${subjectBadgeColor}">${task.subject}</span>
                ${typeBadge}
                ${weightageBadge}
              </div>
              <h3 class="text-base font-bold text-white ${isCompleted ? 'line-through text-slate-400' : ''}">${task.chapter_name}</h3>
              <p class="text-xs text-slate-400 mt-0.5">Chapter ID: <span class="font-mono text-slate-300">${task.chapter_id}</span></p>
            </div>
          </div>

          <div class="text-right flex-shrink-0">
            <div class="text-sm font-bold text-indigo-400 font-mono">${task.allocated_hours} hrs</div>
            <span class="text-[10px] uppercase font-bold tracking-wider ${isCompleted ? 'text-emerald-400' : 'text-amber-400'}">
              ${isCompleted ? '✓ Completed' : 'Pending'}
            </span>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    container.innerHTML = `<div class="p-8 text-center text-rose-400">Failed to load tasks.</div>`;
  }
}

async function toggleTask(taskId, isChecked) {
  const status = isChecked ? "COMPLETED" : "PENDING";
  try {
    await fetch("/api/tasks/toggle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_id: taskId, status })
    });
    // Refresh stats and current day
    fetchTimeline();
    loadDayTasks(currentDay);
  } catch (err) {
    console.error("Failed to toggle task:", err);
  }
}

function changeDay(delta) {
  if (!currentTimeline) return;
  const newDay = currentDay + delta;
  if (newDay >= 1 && newDay <= currentTimeline.total_days) {
    currentDay = newDay;
    loadDayTasks(currentDay);
  }
}

function jumpToDay(val) {
  const day = parseInt(val, 10);
  if (currentTimeline && day >= 1 && day <= currentTimeline.total_days) {
    currentDay = day;
    loadDayTasks(currentDay);
  }
}

function getSubjectColorClass(subject) {
  switch (subject) {
    case "Botany": return "text-emerald-400";
    case "Zoology": return "text-cyan-400";
    case "Physics": return "text-indigo-400";
    case "Chemistry": return "text-amber-400";
    default: return "text-pink-400";
  }
}

// HOUR GUIDE CALCULATOR
async function loadHourGuide(hours) {
  try {
    const res = await fetch(`/api/guidelines?hours=${hours}`);
    const data = await res.json();
    document.getElementById("slider-hours-display").textContent = `${hours.toFixed(1)} Hours/Day`;
    document.getElementById("guide-botany-hours").textContent = `${data.botany_hours} hrs`;
    document.getElementById("guide-zoology-hours").textContent = `${data.zoology_hours} hrs`;
    document.getElementById("guide-physics-hours").textContent = `${data.physics_hours} hrs`;
    document.getElementById("guide-chemistry-hours").textContent = `${data.chemistry_hours} hrs`;
    document.getElementById("guide-revision-hours").textContent = `${data.revision_hours} hrs`;
    document.getElementById("guide-weekly-hours").textContent = `${data.weekly_hours} Hours / Week`;
  } catch (err) {
    console.error(err);
  }
}

function updateHourGuide(val) {
  loadHourGuide(parseFloat(val));
}

// TEST ARENA
let activeQuestions = [];

async function loadTestQuestions() {
  const subject = document.getElementById("select-test-subject").value;
  const container = document.getElementById("test-questions-list");
  container.innerHTML = `<div class="p-8 text-center text-slate-500">Loading questions for ${subject}...</div>`;

  try {
    const res = await fetch(`/api/questions?subject=${encodeURIComponent(subject)}`);
    activeQuestions = await res.json();

    if (!activeQuestions || activeQuestions.length === 0) {
      container.innerHTML = `<div class="p-8 text-center text-slate-400">No questions found for this subject filter.</div>`;
      return;
    }

    container.innerHTML = activeQuestions.map((q, idx) => {
      const isMCQ = q.type === "MCQ";
      const subjectColor = getSubjectColorClass(q.subject);

      return `
        <div class="p-5 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
          <div class="flex items-center justify-between text-xs">
            <span class="font-bold ${subjectColor}">Q${idx + 1} • ${q.subject}</span>
            <span class="text-slate-400">${q.chapter}</span>
          </div>

          <p class="text-sm sm:text-base font-semibold text-white">${q.question}</p>

          ${isMCQ ? `
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2">
              ${q.options.map(opt => `
                <label class="flex items-center gap-3 p-3 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 cursor-pointer text-sm text-slate-200">
                  <input type="radio" name="q_${q.id}" value="${opt}" class="accent-indigo-500" />
                  <span>${opt}</span>
                </label>
              `).join("")}
            </div>
          ` : `
            <div class="pt-2">
              <label class="block text-xs text-slate-400 mb-1 font-medium">Type your answer / term:</label>
              <input type="text" name="q_${q.id}" placeholder="e.g. RuBisCO or 500" class="w-full px-3.5 py-2.5 rounded-lg bg-slate-900 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500" />
            </div>
          `}
        </div>
      `;
    }).join("");
  } catch (err) {
    container.innerHTML = `<div class="p-8 text-center text-rose-400">Failed to load questions.</div>`;
  }
}

async function submitTest(e) {
  e.preventDefault();
  const form = document.getElementById("test-form");
  const formData = new FormData(form);
  const submissions = [];

  activeQuestions.forEach(q => {
    const val = formData.get(`q_${q.id}`) || "";
    submissions.push({
      question_id: q.id,
      user_answer: val
    });
  });

  const subject = document.getElementById("select-test-subject").value;

  try {
    const res = await fetch("/api/test/grade", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        test_type: "NEET_ARENA_PRACTICE",
        subject: subject,
        submissions: submissions
      })
    });
    const result = await res.json();
    displayTestResults(result);
  } catch (err) {
    alert("Grading failed: " + err.message);
  }
}

function displayTestResults(result) {
  const panel = document.getElementById("test-results-panel");
  panel.classList.remove("hidden");
  panel.scrollIntoView({ behavior: 'smooth' });

  document.getElementById("res-score").textContent = `${result.score} / ${result.max_score}`;
  document.getElementById("res-accuracy").textContent = `${result.percentage}%`;
  document.getElementById("res-correct").textContent = result.correct_count;
  document.getElementById("res-incorrect").textContent = result.incorrect_count;

  const explContainer = document.getElementById("res-explanations-list");
  explContainer.innerHTML = result.details.map(d => {
    return `
      <div class="p-4 rounded-lg ${d.is_correct ? 'bg-emerald-950/20 border border-emerald-800/40' : d.is_unattempted ? 'bg-slate-900 border border-slate-800' : 'bg-rose-950/20 border border-rose-800/40'} text-xs">
        <div class="flex items-center justify-between font-bold mb-1">
          <span class="${d.is_correct ? 'text-emerald-400' : d.is_unattempted ? 'text-slate-400' : 'text-rose-400'}">
            ${d.is_correct ? '✓ Correct (+4)' : d.is_unattempted ? '— Unattempted (0)' : '✗ Incorrect (-1)'}
          </span>
          <span class="text-slate-400">${d.subject} • ${d.chapter}</span>
        </div>
        <p class="font-semibold text-slate-200 mb-2">${d.question}</p>
        <p class="text-slate-300">Your answer: <span class="font-mono ${d.is_correct ? 'text-emerald-300' : 'text-rose-300'}">${d.user_answer || '(None)'}</span></p>
        <p class="text-slate-300">Correct answer: <span class="font-mono text-emerald-400 font-bold">${d.correct_answer}</span></p>
        ${d.explanation ? `<p class="mt-2 text-slate-400 border-t border-slate-800/60 pt-1.5"><strong class="text-slate-300">Explanation:</strong> ${d.explanation}</p>` : ''}
      </div>
    `;
  }).join("");
}

function closeTestResults() {
  document.getElementById("test-results-panel").classList.add("hidden");
}

function startTestTimer() {
  if (testTimer) {
    clearInterval(testTimer);
    testTimer = null;
    document.getElementById("btn-timer-toggle").classList.remove("text-rose-400");
    document.getElementById("btn-timer-toggle").classList.add("text-emerald-400");
    return;
  }

  document.getElementById("btn-timer-toggle").classList.remove("text-emerald-400");
  document.getElementById("btn-timer-toggle").classList.add("text-rose-400");

  testTimer = setInterval(() => {
    if (timerSeconds <= 0) {
      clearInterval(testTimer);
      alert("⏱️ Time is up! Submitting test automatically...");
      document.getElementById("test-form").requestSubmit();
      return;
    }
    timerSeconds--;
    const mins = Math.floor(timerSeconds / 60);
    const secs = timerSeconds % 60;
    document.getElementById("test-timer-display").textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }, 1000);
}

// MISTAKE NOTEBOOK
async function loadMistakes() {
  const container = document.getElementById("mistakes-list");
  container.innerHTML = `<div class="p-8 text-center text-slate-500">Loading unresolved mistakes...</div>`;

  try {
    const res = await fetch("/api/mistakes?unresolved=true");
    const mistakes = await res.json();

    if (!mistakes || mistakes.length === 0) {
      container.innerHTML = `
        <div class="p-8 rounded-xl bg-slate-950 border border-slate-800 text-center text-slate-400">
          <span class="text-3xl">🎉</span>
          <p class="text-base font-bold text-emerald-400 mt-2">Zero Unresolved Mistakes!</p>
          <p class="text-xs text-slate-500 mt-1">Take tests in the Test Arena. Any wrong answer will be saved here automatically.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = mistakes.map(m => {
      const subjectColor = getSubjectColorClass(m.subject);
      return `
        <div class="p-5 rounded-xl bg-slate-950 border border-rose-500/20 space-y-2">
          <div class="flex items-center justify-between text-xs">
            <span class="font-bold ${subjectColor}">${m.subject} • ${m.chapter}</span>
            <button onclick="resolveMistake(${m.mistake_id})" class="px-3 py-1 rounded-md bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 font-bold transition">
              ✓ Mark Mastered
            </button>
          </div>
          <p class="text-sm font-semibold text-white">${m.question}</p>
          <div class="text-xs space-y-1">
            <p class="text-rose-400">Your wrong attempt: <span class="font-mono font-bold">${m.user_answer}</span></p>
            <p class="text-emerald-400">Correct NCERT answer: <span class="font-mono font-bold">${m.correct_answer}</span></p>
          </div>
          ${m.explanation ? `<p class="text-xs text-slate-400 pt-2 border-t border-slate-900"><strong class="text-slate-300">NCERT Insight:</strong> ${m.explanation}</p>` : ''}
        </div>
      `;
    }).join("");
  } catch (err) {
    container.innerHTML = `<div class="p-8 text-center text-rose-400">Failed to load mistake notebook.</div>`;
  }
}

async function resolveMistake(mistakeId) {
  try {
    await fetch("/api/mistakes/resolve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mistake_id: mistakeId })
    });
    loadMistakes();
  } catch (err) {
    console.error(err);
  }
}

// SYLLABUS EXPLORER
async function loadChapters() {
  try {
    const res = await fetch("/api/chapters");
    allChapters = await res.json();
    renderSyllabusGrid();
  } catch (err) {
    console.error("Failed to load chapters:", err);
  }
}

function renderSyllabusGrid() {
  const container = document.getElementById("syllabus-grid");
  if (!container || !allChapters) return;

  const filter = document.getElementById("syllabus-filter-subject").value;
  const filtered = filter === "ALL" ? allChapters : allChapters.filter(c => c.subject.toLowerCase() === filter.toLowerCase());

  container.innerHTML = filtered.map(c => {
    const subjectColor = getSubjectColorClass(c.subject);
    const weightageBadge = c.weightage === "High" ? "bg-rose-500/10 text-rose-400 border-rose-500/20" : "bg-slate-800 text-slate-300 border-slate-700";

    return `
      <div class="p-5 rounded-xl bg-slate-950 border border-slate-800/80 hover:border-slate-700 transition">
        <div class="flex items-center justify-between text-xs mb-2">
          <span class="font-bold ${subjectColor}">${c.subject} • Class ${c.class_level}</span>
          <span class="px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wider ${weightageBadge}">${c.weightage} Weightage</span>
        </div>
        <h4 class="text-base font-bold text-white mb-2">${c.name}</h4>
        <div class="text-xs text-slate-400 flex items-center justify-between border-t border-slate-900 pt-2">
          <span>Est. Hours: <strong class="text-indigo-400">${c.est_study_hours} hrs</strong></span>
          <span>Avg Qs: <strong class="text-white">${c.avg_questions} / yr</strong></span>
        </div>
      </div>
    `;
  }).join("");
}

function filterSyllabus() {
  renderSyllabusGrid();
}

// MODAL HANDLERS
function openTimelineModal() {
  document.getElementById("modal-timeline").classList.remove("hidden");
  if (currentTimeline) {
    const daysInput = document.getElementById("input-total-days");
    if (daysInput) {
      daysInput.value = currentTimeline.total_days;
      handleDaysInputChange(currentTimeline.total_days);
    }
  }
}

function closeTimelineModal() {
  document.getElementById("modal-timeline").classList.add("hidden");
}

function handleDaysInputChange(val) {
  const days = parseInt(val, 10);
  const preview = document.getElementById("timeline-months-preview");
  const nameInput = document.getElementById("input-plan-name");
  if (!isNaN(days) && days > 0) {
    const months = (days / 30).toFixed(1);
    if (preview) preview.textContent = `~${months} Months`;
    if (nameInput) {
      nameInput.value = `${days}-Day NEET Preparation Plan`;
    }
  }
}

function setPresetDays(days) {
  const input = document.getElementById("input-total-days");
  if (input) {
    input.value = days;
    handleDaysInputChange(days);
  }
}

async function handleCreateTimeline(e) {
  e.preventDefault();
  const name = document.getElementById("input-plan-name").value;
  const totalDays = parseInt(document.getElementById("input-total-days").value, 10);
  const dailyHours = parseFloat(document.getElementById("input-daily-hours").value);
  const startDate = document.getElementById("input-start-date").value;

  if (isNaN(totalDays) || totalDays < 5) {
    alert("Please enter a valid timeline of at least 5 days.");
    return;
  }

  try {
    const res = await fetch("/api/timeline", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        total_days: totalDays,
        daily_hours: dailyHours,
        start_date: startDate
      })
    });
    const data = await res.json();
    closeTimelineModal();
    alert(`🎉 ${data.message}! Custom ${totalDays}-day roadmap generated with High-Yield subjects first!`);
    currentDay = 1;
    await fetchTimeline();
  } catch (err) {
    alert("Error creating timeline: " + err.message);
  }
}

function openStudyLogModal() {
  document.getElementById("modal-log-study").classList.remove("hidden");
}

function closeStudyLogModal() {
  document.getElementById("modal-log-study").classList.add("hidden");
}

async function handleSaveStudyLog(e) {
  e.preventDefault();
  const logDate = document.getElementById("log-date").value;
  const botany = parseFloat(document.getElementById("log-botany").value || 0);
  const zoology = parseFloat(document.getElementById("log-zoology").value || 0);
  const physics = parseFloat(document.getElementById("log-physics").value || 0);
  const chemistry = parseFloat(document.getElementById("log-chemistry").value || 0);
  const revision = parseFloat(document.getElementById("log-revision").value || 0);

  try {
    await fetch("/api/study_log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        log_date: logDate,
        botany_hours: botany,
        zoology_hours: zoology,
        physics_hours: physics,
        chemistry_hours: chemistry,
        revision_hours: revision
      })
    });
    closeStudyLogModal();
    alert("Study log saved successfully!");
  } catch (err) {
    alert("Error saving log: " + err.message);
  }
}
