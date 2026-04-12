const profileSelect = document.querySelector("#profileSelect");
const refreshProfilesButton = document.querySelector("#refreshProfilesButton");
const messageInput = document.querySelector("#messageInput");
const sendButton = document.querySelector("#sendButton");
const copyButton = document.querySelector("#copyButton");
const statusText = document.querySelector("#statusText");
const responseOutput = document.querySelector("#responseOutput");
const documentInput = document.querySelector("#documentInput");
const documentInstructionInput = document.querySelector("#documentInstructionInput");
const teamContextInput = document.querySelector("#teamContextInput");
const processDocumentButton = document.querySelector("#processDocumentButton");
const documentMeta = document.querySelector("#documentMeta");
const documentExtractOutput = document.querySelector("#documentExtractOutput");
const documentSummaryOutput = document.querySelector("#documentSummaryOutput");
const documentStructuredOutput = document.querySelector("#documentStructuredOutput");
const documentExecutionOutput = document.querySelector("#documentExecutionOutput");
const copyExtractedButton = document.querySelector("#copyExtractedButton");
const copySummaryButton = document.querySelector("#copySummaryButton");
const copyStructuredButton = document.querySelector("#copyStructuredButton");
const copyExecutionButton = document.querySelector("#copyExecutionButton");
const saveProjectContextButton = document.querySelector("#saveProjectContextButton");
const systemPromptInput = document.querySelector("#systemPromptInput");
const refreshRagButton = document.querySelector("#refreshRagButton");
const ragStats = document.querySelector("#ragStats");
const ragDbPath = document.querySelector("#ragDbPath");
const ragDocumentList = document.querySelector("#ragDocumentList");
const ragSourceOutput = document.querySelector("#ragSourceOutput");
const ragFilterDocumentType = document.querySelector("#ragFilterDocumentType");
const ragFilterMinistry = document.querySelector("#ragFilterMinistry");
const ragFilterAgency = document.querySelector("#ragFilterAgency");
const ragFilterRdType = document.querySelector("#ragFilterRdType");
const ragFilterBusinessType = document.querySelector("#ragFilterBusinessType");
const refreshIngestionButton = document.querySelector("#refreshIngestionButton");
const ingestionStats = document.querySelector("#ingestionStats");
const ingestionReviewList = document.querySelector("#ingestionReviewList");
const navButtons = Array.from(document.querySelectorAll(".nav-button[data-target-view]"));
const workspaceViews = Array.from(document.querySelectorAll(".workspace-view[data-view]"));
const proposalOpsOutput = document.querySelector("#proposalOpsOutput");
const copyProposalOpsButton = document.querySelector("#copyProposalOpsButton");
const announcementAgentMeta = document.querySelector("#announcementAgentMeta");
const announcementFolderInput = document.querySelector("#announcementFolderInput");
const runAnnouncementAgentButton = document.querySelector("#runAnnouncementAgentButton");
const copyAnnouncementAgentButton = document.querySelector("#copyAnnouncementAgentButton");
const announcementFolderMeta = document.querySelector("#announcementFolderMeta");
const announcementAgentOutput = document.querySelector("#announcementAgentOutput");
const announcementDashboardOutput = document.querySelector("#announcementDashboardOutput");
const announcementFeedbackInput = document.querySelector("#announcementFeedbackInput");
const saveAnnouncementFeedbackButton = document.querySelector("#saveAnnouncementFeedbackButton");
let lastAnnouncementAgentPayload = null;

async function loadProfiles() {
  setStatus("프로필을 불러오는 중...");
  const response = await fetch("/api/profiles");
  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.error || "프로필을 불러오지 못했습니다.");
  }

  profileSelect.innerHTML = "";
  for (const profile of payload.profiles) {
    const option = document.createElement("option");
    option.value = profile.name;
    option.textContent = `${profile.name} (${profile.model})`;
    if (profile.active) {
      option.selected = true;
    }
    profileSelect.appendChild(option);
  }

  setStatus(`프로필 ${payload.profiles.length}개를 불러왔습니다.`);
}

function setStatus(message) {
  statusText.textContent = message;
}

function setBusyState(isBusy) {
  sendButton.disabled = isBusy;
  processDocumentButton.disabled = isBusy;
  saveProjectContextButton.disabled = isBusy;
  refreshRagButton.disabled = isBusy;
  refreshIngestionButton.disabled = isBusy;
  runAnnouncementAgentButton.disabled = isBusy;
  saveAnnouncementFeedbackButton.disabled = isBusy;
}

function switchView(viewName) {
  for (const view of workspaceViews) {
    view.classList.toggle("is-active", view.dataset.view === viewName);
  }
  for (const button of navButtons) {
    button.classList.toggle("is-active", button.dataset.targetView === viewName);
  }
  if (viewName === "documents") {
    void Promise.all([loadRagDocuments(), loadIngestionState()]).catch((error) => {
      setStatus(String(error.message || error));
    });
  }
}

function formatRagSources(rag) {
  if (!rag || !Array.isArray(rag.sources) || rag.sources.length === 0) {
    return "아직 검색 출처가 없습니다.";
  }
  const filterSummary = formatAppliedRagFilters(rag.applied_filters);
  const lines = rag.sources
    .map((source) => {
      const score = typeof source.score === "number" ? source.score.toFixed(4) : "해당 없음";
      const metadata = [
        source.document_type ? `유형=${formatDocumentType(source.document_type)}` : "",
        source.title ? `제목=${source.title}` : "",
        source.ministry ? `부처=${source.ministry}` : "",
        source.agency ? `기관=${source.agency}` : "",
        source.rd_or_non_rd ? `R&D=${formatRdType(source.rd_or_non_rd)}` : "",
        source.business_type ? `사업=${source.business_type}` : "",
      ]
        .filter(Boolean)
        .join(" | ");
      return `${source.file_name} #${source.chunk_index} 점수 ${score}${metadata ? ` | ${metadata}` : ""}`;
    });
  if (filterSummary) {
    lines.push(`필터: ${filterSummary}`);
  }
  return lines.join("\n");
}

function formatAppliedRagFilters(filters) {
  if (!filters || typeof filters !== "object") {
    return "";
  }
  return Object.entries(filters)
    .filter(([, value]) => value)
    .map(([key, value]) => `${key}=${value}`)
    .join(", ");
}

function renderRagDocuments(payload) {
  const documents = Array.isArray(payload.documents) ? payload.documents : [];
  ragStats.textContent = `문서 ${payload.indexed_document_count || 0}개, 청크 ${payload.indexed_chunk_count || 0}개`;
  ragDbPath.textContent = payload.db_path ? `DB: ${payload.db_path}` : "DB 경로를 확인할 수 없습니다.";
  ragDocumentList.innerHTML = "";

  if (documents.length === 0) {
    const empty = document.createElement("p");
    empty.className = "helper-text";
    empty.textContent = "아직 색인된 RAG 문서가 없습니다.";
    ragDocumentList.appendChild(empty);
    return;
  }

  for (const documentItem of documents) {
    const item = document.createElement("article");
    item.className = "rag-document-item";
    item.dataset.documentId = String(documentItem.id);
    item.tabIndex = 0;
    item.setAttribute("role", "button");
    item.setAttribute("aria-label", `${documentItem.file_name || `문서 ${documentItem.id}`} 열기`);

    const details = document.createElement("div");
    const title = document.createElement("h3");
    title.textContent = documentItem.title || documentItem.file_name || `문서 ${documentItem.id}`;
    const summary = document.createElement("p");
    summary.textContent = [
      documentItem.document_type ? `유형 ${formatDocumentType(documentItem.document_type)}` : "유형 미분류",
      documentItem.ministry ? `부처 ${documentItem.ministry}` : "",
      documentItem.agency ? `기관 ${documentItem.agency}` : "",
      documentItem.business_type ? `사업 ${documentItem.business_type}` : "",
      documentItem.submission_deadline ? `마감 ${documentItem.submission_deadline}` : "",
    ]
      .filter(Boolean)
      .join(" | ");
    const meta = document.createElement("p");
    meta.textContent = [
      `식별자 ${documentItem.id}`,
      documentItem.file_name ? `파일 ${documentItem.file_name}` : "",
      `청크 ${documentItem.chunk_count || 0}개`,
      documentItem.embedding_profile ? `임베딩 ${documentItem.embedding_profile}` : "임베딩 미확인",
      documentItem.chat_profile ? `챗 ${documentItem.chat_profile}` : "챗 프로필 미확인",
    ]
      .filter(Boolean)
      .join(" | ");
    details.appendChild(title);
    if (summary.textContent) {
      details.appendChild(summary);
    }
    details.appendChild(meta);

    const actions = document.createElement("div");
    actions.className = "rag-document-actions";
    const reindexButton = document.createElement("button");
    reindexButton.className = "ghost-button";
    reindexButton.type = "button";
    reindexButton.dataset.action = "reindex";
    reindexButton.dataset.documentId = String(documentItem.id);
    reindexButton.textContent = "재색인";
    const viewButton = document.createElement("button");
    viewButton.className = "ghost-button";
    viewButton.type = "button";
    viewButton.dataset.action = "view";
    viewButton.dataset.documentId = String(documentItem.id);
    viewButton.textContent = "열기";
    const deleteButton = document.createElement("button");
    deleteButton.className = "ghost-button danger-button";
    deleteButton.type = "button";
    deleteButton.dataset.action = "delete";
    deleteButton.dataset.documentId = String(documentItem.id);
    deleteButton.textContent = "삭제";
    actions.appendChild(viewButton);
    actions.appendChild(reindexButton);
    actions.appendChild(deleteButton);

    item.appendChild(details);
    item.appendChild(actions);
    ragDocumentList.appendChild(item);
  }
}

async function loadRagDocuments() {
  const response = await fetch("/api/rag/documents");
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "RAG 문서를 불러오지 못했습니다.");
  }
  renderRagDocuments(payload);
}

function renderIngestionState(payload) {
  const summary = payload.summary || {};
  const reviewItems = Array.isArray(payload.review_items) ? payload.review_items : [];
  ingestionStats.textContent = [
    `소스 ${summary.source_count || 0}개`,
    `계획 ${summary.plan_count || 0}개`,
    `작업 ${summary.job_count || 0}개`,
    `검수 항목 ${summary.review_item_count || 0}개`,
    `검수 필요 ${summary.needs_review_count || 0}개`,
    `승인 ${summary.approved_count || 0}개`,
  ].join(" | ");
  ingestionReviewList.innerHTML = "";

  if (reviewItems.length === 0) {
    const empty = document.createElement("p");
    empty.className = "helper-text";
    empty.textContent = "아직 수집 검수 항목이 없습니다.";
    ingestionReviewList.appendChild(empty);
    return;
  }

  for (const item of reviewItems) {
    const row = document.createElement("article");
    row.className = "ingestion-review-item";
    const details = document.createElement("div");
    const title = document.createElement("h3");
    title.textContent = item.file_name || item.source_uri || `검수 항목 ${item.id}`;
    const meta = document.createElement("p");
    meta.textContent = [
      `상태 ${formatReviewStatus(item.review_status)}`,
      item.document_id ? `문서 ${item.document_id}` : "",
      item.quality_score !== null && item.quality_score !== undefined ? `품질 ${item.quality_score}` : "",
      item.source_uri ? `출처 ${item.source_uri}` : "",
    ]
      .filter(Boolean)
      .join(" | ");
    const notes = document.createElement("p");
    notes.textContent = item.notes || "검수 메모가 없습니다.";
    details.appendChild(title);
    details.appendChild(meta);
    details.appendChild(notes);

    const actions = document.createElement("div");
    actions.className = "rag-document-actions";
    for (const status of ["approved", "rejected", "needs_review"]) {
      const button = document.createElement("button");
      button.className = "ghost-button";
      if (status === "rejected") {
        button.classList.add("danger-button");
      }
      button.type = "button";
      button.dataset.reviewItemId = String(item.id);
      button.dataset.reviewStatus = status;
      button.textContent = formatReviewStatus(status);
      actions.appendChild(button);
    }

    row.appendChild(details);
    row.appendChild(actions);
    ingestionReviewList.appendChild(row);
  }
}

async function loadIngestionState() {
  const response = await fetch("/api/ingestion/state");
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "수집 상태를 불러오지 못했습니다.");
  }
  renderIngestionState(payload);
}

async function updateIngestionReviewStatus(reviewItemId, reviewStatus) {
  setBusyState(true);
  setStatus(`검수 항목 ${reviewItemId} 업데이트 중...`);
  try {
    const response = await fetch("/api/ingestion/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        review_item_id: Number(reviewItemId),
        review_status: reviewStatus,
        notes: reviewStatus === "approved" ? "문서 대시보드에서 승인됨." : "",
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "수집 검수 항목을 업데이트하지 못했습니다.");
    }
    renderIngestionState(payload);
    setStatus(`검수 항목 ${reviewItemId} 상태: ${formatReviewStatus(reviewStatus)}.`);
  } catch (error) {
    setStatus(String(error.message || error));
  } finally {
    setBusyState(false);
  }
}

async function loadProjectContext() {
  const response = await fetch("/api/project-context");
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "프로젝트 문맥을 불러오지 못했습니다.");
  }
  systemPromptInput.value = payload.system_prompt || "";
  documentInstructionInput.value = payload.instruction || "";
  teamContextInput.value = payload.team_context || "";
}

async function saveProjectContext() {
  setBusyState(true);
  setStatus("프로젝트 문맥 저장 중...");
  try {
    const response = await fetch("/api/project-context", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        system_prompt: systemPromptInput.value.trim(),
        instruction: documentInstructionInput.value.trim(),
        team_context: teamContextInput.value.trim(),
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "프로젝트 문맥을 저장하지 못했습니다.");
    }
    systemPromptInput.value = payload.system_prompt || "";
    documentInstructionInput.value = payload.instruction || "";
    teamContextInput.value = payload.team_context || "";
    setStatus("프로젝트 문맥을 저장했습니다.");
  } catch (error) {
    setStatus(String(error.message || error));
  } finally {
    setBusyState(false);
  }
}

async function openRagDocument(documentId) {
  setStatus(`RAG 문서 ${documentId} 여는 중...`);
  try {
    const response = await fetch(`/api/rag/document?document_id=${encodeURIComponent(documentId)}`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "RAG 문서를 열지 못했습니다.");
    }
    renderDocumentDetail(payload);
    setStatus(`${payload.file_name} 문서를 열었습니다.`);
  } catch (error) {
    setStatus(String(error.message || error));
  }
}

function renderDocumentDetail(payload) {
  const metadata = payload.metadata || {};
  const structured = payload.structured || {};
  const chunkFallback = Array.isArray(payload.chunks)
    ? payload.chunks.map((chunk) => `#${chunk.chunk_index}\n${chunk.text}`).join("\n\n")
    : "";
  const extractedText = payload.extracted_text || chunkFallback || "(저장된 텍스트 없음)";
  documentMeta.textContent = [
    payload.file_name || `문서 ${payload.id}`,
    metadata.document_type ? `유형 ${formatDocumentType(metadata.document_type)}` : "",
    metadata.ministry ? `부처 ${metadata.ministry}` : "",
    metadata.agency ? `기관 ${metadata.agency}` : "",
    metadata.submission_deadline ? `마감 ${metadata.submission_deadline}` : "",
    payload.artifact_available ? "저장된 분석 결과 있음" : "저장된 청크만 표시 중",
  ]
    .filter(Boolean)
    .join(" | ");
  documentExtractOutput.textContent = extractedText;
  documentSummaryOutput.textContent = payload.summary || "(저장된 요약 없음)";
  documentStructuredOutput.textContent =
    structured && Object.keys(structured).length > 0
      ? formatStructuredInsights(structured)
      : "(저장된 구조화 분석 결과 없음)";
  documentExecutionOutput.textContent =
    structured && Object.keys(structured).length > 0
      ? formatExecutionPlan(structured)
      : "(저장된 내부 실행계획 없음)";
}

async function runRagDocumentAction(action, documentId) {
  if (action === "view") {
    await openRagDocument(documentId);
    return;
  }
  if (action === "delete" && !window.confirm(`RAG 문서 ${documentId}을 삭제할까요?`)) {
    return;
  }
  const endpoint = action === "delete" ? "/api/rag/delete" : "/api/rag/reindex";
  const body = { document_id: Number(documentId) };
  if (action === "reindex") {
    body.profile = profileSelect.value;
  }

  setBusyState(true);
  setStatus(`RAG 문서 ${documentId} ${action === "delete" ? "삭제" : "재색인"} 중...`);
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "RAG 문서 작업에 실패했습니다.");
    }
    renderRagDocuments(payload);
    setStatus(`RAG 문서 ${documentId} ${action === "delete" ? "삭제 완료" : "재색인 완료"}.`);
  } catch (error) {
    setStatus(String(error.message || error));
  } finally {
    setBusyState(false);
  }
}

function formatRagStatus(rag) {
  if (!rag || typeof rag !== "object") {
    return "RAG 상태를 확인할 수 없습니다.";
  }
  if (rag.enabled) {
    const sourceCount = Array.isArray(rag.sources) ? rag.sources.length : 0;
    if (sourceCount > 0) {
      return `RAG가 ${rag.embedding_profile}로 검색한 청크 ${sourceCount}개를 사용했습니다.`;
    }
    return `RAG가 ${rag.embedding_profile}로 청크 ${rag.indexed_chunk_count || 0}개를 색인했습니다.`;
  }
  if (rag.error) {
    return `RAG 미사용: ${rag.error}`;
  }
  return rag.reason || "아직 RAG를 사용하지 않았습니다.";
}

function formatProposalOpsPlan(plan) {
  if (!plan || typeof plan !== "object") {
    return "아직 제안 운영 계획이 없습니다.";
  }
  const summary = plan.project_summary || {};
  const lines = [];
  lines.push("사업 요약");
  lines.push(`- 제목: ${summary.title || "미확인"}`);
  lines.push(`- 원본 파일: ${summary.source_file || "미확인"}`);
  lines.push(`- 프로젝트 유형: ${summary.project_type || "미확인"}`);
  lines.push(`- 사업 유형: ${summary.business_type || "미확인"}`);
  lines.push(`- 제출 마감: ${summary.submission_deadline || "검토 필요"}`);
  lines.push(`- 제출 채널: ${summary.submission_channel || "검토 필요"}`);

  appendObjectList(lines, "제출 체크리스트", plan.submission_checklist, (item) =>
    `- [${formatReviewStatus(item.status || "needs_review")}] ${item.item || "이름 없는 항목"} | 담당: ${item.owner || "미배정"}${item.basis ? ` | 근거: ${item.basis}` : ""}`
  );
  appendObjectList(lines, "관리자 확인 질문", plan.manager_questions, (item) =>
    `- ${item.question || "미정 질문"} | 대상: ${item.target || "미배정"} | 사유: ${item.reason || "검토"}`
  );
  appendObjectList(lines, "역할별 업무", plan.role_tasks, (item) => {
    const tasks = Array.isArray(item.tasks) ? item.tasks.join("; ") : "등록된 업무 없음";
    return `- ${item.role || "역할"} / ${item.owner || "미배정"}: ${tasks}${item.manager_plus_one ? ` | +1: ${item.manager_plus_one}` : ""}`;
  });
  appendObjectList(lines, "리마인드 계획", plan.reminder_plan, (item) =>
    `- ${item.phase || "단계"}: ${item.cadence || "주기"} | ${item.target || "대상"} | ${item.condition || "조건"}`
  );
  appendTextList(lines, "폴더 계획", plan.folder_plan);
  appendTextList(lines, "파일 산출물 계획", plan.file_plan);
  appendTextList(lines, "실행 미리보기", plan.execution_preview);
  appendTextList(lines, "추가 입력 필요사항", plan.needs_manual_inputs);
  return lines.join("\n").trim();
}

function formatAnnouncementAgentMeta(agent) {
  if (!agent || typeof agent !== "object" || !agent.enabled) {
    return "아직 생성된 파일이 없습니다.";
  }
  return [
    `생성 폴더: ${agent.project_dir || "미확인"}`,
    `저장된 원본 파일: ${Array.isArray(agent.saved_source_files) ? agent.saved_source_files.length : 0}`,
    `총괄장: ${agent.summary_workbook || "미생성"}`,
    `공고 모니터링: ${agent.monitoring_workbook || "미생성"}`,
  ].join("\n");
}

function formatAnnouncementAgentBundleResult(payload) {
  const agent = payload?.announcement_agent || {};
  if (!agent.enabled) {
    return "공고 에이전트 실행 결과가 없습니다.";
  }
  const row = agent.monitoring_row || {};
  const generatedFiles = Array.isArray(agent.generated_files) ? agent.generated_files : [];
  const savedSourceFiles = Array.isArray(agent.saved_source_files) ? agent.saved_source_files : [];
  const lines = [
    `처리 파일 수: ${payload.file_count || savedSourceFiles.length || 0}`,
    `대표 공고 파일: ${payload.primary_file_name || row.source_file || "확인 필요"}`,
    `생성 폴더: ${agent.project_dir || "확인 필요"}`,
    `폴더명: ${agent.folder_name || "확인 필요"}`,
    `총괄장: ${agent.summary_workbook || "미생성"}`,
    `첨부파일목록: ${agent.attachment_manifest || "미생성"}`,
    `공고리스트: ${agent.monitoring_workbook || "미생성"}`,
    `공고리스트 원장: ${agent.monitoring_json || "미생성"}`,
    `저장된 업로드 파일: ${savedSourceFiles.length}`,
  ];
  if (generatedFiles.length > 0) {
    lines.push("");
    lines.push("생성 파일");
    for (const filePath of generatedFiles) {
      lines.push(`- ${filePath}`);
    }
  }
  lines.push("");
  lines.push("공고목록 행");
  lines.push(`- 업로드일자: ${row.uploaded_at || ""}`);
  lines.push(`- 부처: ${row.ministry || ""}`);
  lines.push(`- 전문기관: ${row.agency || ""}`);
  lines.push(`- 사업구분: ${row.business_type || ""}`);
  lines.push(`- 사업분야: ${row.business_domain || ""}`);
  lines.push(`- 사업명: ${row.program_name || ""}`);
  lines.push(`- 접수마감일자: ${row.submission_deadline || ""}`);
  return lines.join("\n").trim();
}

function formatAnnouncementDashboard(stats) {
  if (!stats || typeof stats !== "object") {
    return "아직 대시보드 결과가 없습니다.";
  }
  const lines = [`총 공고 수: ${stats.total_count || 0}`];
  appendCountGroup(lines, "일자별 업로드 수량", stats.by_upload_date);
  appendCountGroup(lines, "부처별", stats.by_ministry);
  appendCountGroup(lines, "사업유형별", stats.by_business_type);
  appendCountGroup(lines, "사업분야별", stats.by_business_domain);
  return lines.join("\n").trim();
}

function appendCountGroup(lines, title, counts) {
  if (!counts || typeof counts !== "object") {
    return;
  }
  lines.push("");
  lines.push(title);
  const entries = Object.entries(counts);
  if (entries.length === 0) {
    lines.push("- 없음");
    return;
  }
  for (const [label, count] of entries) {
    lines.push(`- ${label}: ${count}`);
  }
}

function formatReviewStatus(status) {
  const labels = {
    approved: "승인",
    rejected: "반려",
    needs_review: "검수 필요",
    failed: "실패",
    stale: "오래됨",
  };
  return labels[status] || status || "미확인";
}

function formatDocumentType(documentType) {
  const labels = {
    announcement: "공고",
    regulation: "규정",
    technical: "기술자료",
    company_team: "회사/팀 자료",
    unknown: "미분류",
  };
  return labels[documentType] || documentType || "미분류";
}

function formatRdType(rdType) {
  const labels = {
    rd: "R&D",
    non_rd: "비R&D",
  };
  return labels[rdType] || rdType || "미확인";
}

function appendObjectList(lines, title, items, formatter) {
  if (!Array.isArray(items) || items.length === 0) {
    return;
  }
  lines.push("");
  lines.push(title);
  for (const item of items) {
    lines.push(formatter(item || {}));
  }
}

function appendTextList(lines, title, items) {
  if (!Array.isArray(items) || items.length === 0) {
    return;
  }
  lines.push("");
  lines.push(title);
  for (const item of items) {
    lines.push(`- ${item}`);
  }
}

function collectRagFilters() {
  const filters = {
    document_type: ragFilterDocumentType.value.trim(),
    ministry: ragFilterMinistry.value.trim(),
    agency: ragFilterAgency.value.trim(),
    rd_or_non_rd: ragFilterRdType.value.trim(),
    business_type: ragFilterBusinessType.value.trim(),
  };
  return Object.fromEntries(Object.entries(filters).filter(([, value]) => value));
}

async function sendMessage() {
  const message = messageInput.value.trim();
  const profile = profileSelect.value;
  const ragFilters = collectRagFilters();
  const systemPrompt = systemPromptInput.value.trim();

  if (!message) {
    setStatus("먼저 메시지를 입력하세요.");
    messageInput.focus();
    return;
  }

  setBusyState(true);
  responseOutput.textContent = "답변을 기다리는 중...";
  setStatus(`${profile} 프로필로 전송 중...`);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        profile,
        message,
        system_prompt: systemPrompt,
        rag_filters: ragFilters,
      }),
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "요청에 실패했습니다.");
    }

    responseOutput.textContent = payload.answer || "(빈 답변)";
    ragSourceOutput.textContent = formatRagSources(payload.rag);
    setStatus(`${payload.profile} 응답 완료. ${formatRagStatus(payload.rag)}`);
  } catch (error) {
    responseOutput.textContent = String(error.message || error);
    setStatus("요청에 실패했습니다.");
  } finally {
    setBusyState(false);
  }
}

async function copyText(text, emptyFallbackMessage, successMessage) {
  if (!text || text === emptyFallbackMessage) {
    setStatus("아직 복사할 내용이 없습니다.");
    return;
  }
  await navigator.clipboard.writeText(text);
  setStatus(successMessage);
}

async function copyAnswer() {
  await copyText(responseOutput.textContent, "아직 답변이 없습니다.", "답변을 복사했습니다.");
}

function bytesToBase64(bytes) {
  let binary = "";
  const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) {
    const chunk = bytes.subarray(index, index + chunkSize);
    binary += String.fromCharCode(...chunk);
  }
  return btoa(binary);
}

function formatStructuredInsights(structured) {
  if (!structured || typeof structured !== "object") {
    return "아직 구조화 분석 결과가 없습니다.";
  }

  const metadata = structured.metadata || {};
  const overview = structured.announcement_overview || {};
  const consortium = structured.consortium_requirements || {};
  const eligibility = Array.isArray(structured.eligibility_by_role) ? structured.eligibility_by_role : [];
  const strategy = structured.recommended_consortium_strategy || {};
  const budget = structured.budget || {};
  const documents = Array.isArray(structured.submission_documents) ? structured.submission_documents : [];
  const presentation = structured.presentation || {};
  const schedule = structured.application_schedule || {};
  const channel = structured.submission_channel || {};
  const contacts = Array.isArray(structured.contacts) ? structured.contacts : [];
  const risks = structured.risks_and_checks || {};
  const lines = [];

  if (overview.title) {
    lines.push(`제목: ${overview.title}`);
  }
  if (overview.main_purpose) {
    lines.push(`사업목적: ${overview.main_purpose}`);
  }
  if (overview.project_type) {
    lines.push(`프로젝트 유형: ${overview.project_type}`);
  }
  if (overview.support_summary) {
    lines.push(`지원 내용 요약: ${overview.support_summary}`);
  }
  if (metadata.ministry || metadata.agency || metadata.rd_or_non_rd) {
    lines.push("");
    lines.push("출처 메타데이터:");
    if (metadata.ministry) {
      lines.push(`- 부처: ${metadata.ministry}`);
    }
    if (metadata.agency) {
      lines.push(`- 전문기관/전담기관: ${metadata.agency}`);
    }
    if (metadata.rd_or_non_rd) {
      lines.push(`- R&D 구분: ${formatRdType(metadata.rd_or_non_rd)}`);
    }
  }

  lines.push("");
  lines.push("컨소시엄 요건:");
  lines.push(`- 컨소시엄 필수: ${consortium.consortium_required ? "예" : "아니오"}`);
  lines.push(`- 수요기업 필수: ${consortium.demand_company_required ? "예" : "아니오"}`);
  if (Array.isArray(consortium.lead_org_allowed) && consortium.lead_org_allowed.length > 0) {
    lines.push(`- 주관기관 가능 대상: ${consortium.lead_org_allowed.join(", ")}`);
  }
  if (Array.isArray(consortium.partner_org_allowed) && consortium.partner_org_allowed.length > 0) {
    lines.push(`- 공동기관 가능 대상: ${consortium.partner_org_allowed.join(", ")}`);
  }
  lines.push(`- 위탁 가능: ${consortium.subcontractor_allowed ? "예" : "아니오"}`);
  if (Array.isArray(consortium.notes) && consortium.notes.length > 0) {
    lines.push("");
    lines.push("컨소시엄 비고:");
    for (const note of consortium.notes) {
      lines.push(`- ${note}`);
    }
  }

  if (eligibility.length > 0) {
    lines.push("");
    lines.push("역할별 자격:");
    for (const item of eligibility) {
      const entities = Array.isArray(item.eligible_entities) ? item.eligible_entities.join(", ") : "";
      lines.push(`- ${item.role || "미확인 역할"}: ${entities || "자격 대상 미기재"}`);
      if (Array.isArray(item.restrictions) && item.restrictions.length > 0) {
        lines.push(`  제한사항: ${item.restrictions.join("; ")}`);
      }
    }
  }

  if (Array.isArray(strategy.recommended_structure) && strategy.recommended_structure.length > 0) {
    lines.push("");
    lines.push("추천 컨소시엄 전략:");
    for (const item of strategy.recommended_structure) {
      lines.push(`- ${item}`);
    }
  }
  if (Array.isArray(strategy.recommended_role_rr) && strategy.recommended_role_rr.length > 0) {
    lines.push("");
    lines.push("추천 역할/R&R:");
    for (const item of strategy.recommended_role_rr) {
      const roleLine = `${item.role || "미확인 역할"} -> ${item.recommended_entity_type || "미지정 기관유형"}`;
      lines.push(`- ${roleLine}`);
      if (Array.isArray(item.responsibilities) && item.responsibilities.length > 0) {
        lines.push(`  책임: ${item.responsibilities.join("; ")}`);
      }
    }
  }
  if (Array.isArray(strategy.key_differentiators) && strategy.key_differentiators.length > 0) {
    lines.push("");
    lines.push("핵심 차별화 요소:");
    for (const item of strategy.key_differentiators) {
      lines.push(`- ${item}`);
    }
  }

  if (budget.total_amount || budget.matching_requirement || (Array.isArray(budget.by_year) && budget.by_year.length > 0)) {
    lines.push("");
    lines.push("예산:");
    if (budget.total_amount) {
      lines.push(`- 총액: ${budget.total_amount}`);
    }
    if (Array.isArray(budget.by_year) && budget.by_year.length > 0) {
      for (const item of budget.by_year) {
        lines.push(`- ${item.year || "연도"}: ${item.amount || "금액 미기재"}`);
      }
    }
    if (budget.matching_requirement) {
      lines.push(`- 매칭 요건: ${budget.matching_requirement}`);
    }
    if (Array.isArray(budget.additional_info_needed) && budget.additional_info_needed.length > 0) {
      lines.push(`- 추가 확인 필요: ${budget.additional_info_needed.join("; ")}`);
    }
  }

  if (documents.length > 0) {
    lines.push("");
    lines.push("제출서류:");
    for (const item of documents) {
      const requiredFor = Array.isArray(item.required_for) ? item.required_for.join(", ") : "";
      const providedForm = item.provided_form ? "양식 제공" : "외부/미확인";
      lines.push(`- ${item.document_name || "이름 없는 문서"} | 대상: ${requiredFor || "미지정"} | 양식: ${providedForm}`);
      if (item.issuance_source) {
        lines.push(`  발급처: ${item.issuance_source}`);
      }
      if (item.notes) {
        lines.push(`  비고: ${item.notes}`);
      }
    }
  }

  lines.push("");
  lines.push(`발표평가 필요: ${presentation.required ? "예" : "아니오"}`);
  if (presentation.notes) {
    lines.push(`발표 비고: ${presentation.notes}`);
  }

  if (schedule.announcement_date || schedule.start_at || schedule.end_at || schedule.submission_deadline) {
    lines.push("");
    lines.push("접수 일정:");
    if (schedule.announcement_date) {
      lines.push(`- 공고일: ${schedule.announcement_date}`);
    }
    if (schedule.start_at) {
      lines.push(`- 시작: ${schedule.start_at}`);
    }
    if (schedule.end_at) {
      lines.push(`- 종료: ${schedule.end_at}`);
    }
    if (schedule.submission_deadline) {
      lines.push(`- 제출 마감: ${schedule.submission_deadline}`);
    }
    if (Array.isArray(schedule.important_milestones) && schedule.important_milestones.length > 0) {
      for (const item of schedule.important_milestones) {
        lines.push(`- ${item.date || "미확인 날짜"}: ${item.label || "주요 일정"}`);
      }
    }
  }

  if (channel.method || channel.portal_or_address || channel.notes) {
    lines.push("");
    lines.push("접수 채널:");
    if (channel.method) {
      lines.push(`- 방법: ${channel.method}`);
    }
    if (channel.portal_or_address) {
      lines.push(`- 포털/주소: ${channel.portal_or_address}`);
    }
    if (channel.notes) {
      lines.push(`- 비고: ${channel.notes}`);
    }
  }

  if (contacts.length > 0) {
    lines.push("");
    lines.push("문의처:");
    for (const item of contacts) {
      const details = [item.organization, item.name, item.phone, item.email].filter(Boolean).join(" | ");
      lines.push(`- ${details || "미확인 문의처"}`);
      if (item.topic) {
        lines.push(`  주제: ${item.topic}`);
      }
    }
  }

  if (Array.isArray(risks.compliance_risks) && risks.compliance_risks.length > 0) {
    lines.push("");
    lines.push("컴플라이언스 리스크:");
    for (const item of risks.compliance_risks) {
      lines.push(`- ${item}`);
    }
  }
  if (Array.isArray(risks.missing_information) && risks.missing_information.length > 0) {
    lines.push("");
    lines.push("누락/확인 필요 정보:");
    for (const item of risks.missing_information) {
      lines.push(`- ${item}`);
    }
  }
  if (Array.isArray(risks.go_no_go_checks) && risks.go_no_go_checks.length > 0) {
    lines.push("");
    lines.push("제안 여부 판단 체크:");
    for (const item of risks.go_no_go_checks) {
      lines.push(`- ${item}`);
    }
  }

  return lines.join("\n").trim() || "아직 구조화 분석 결과가 없습니다.";
}

function formatExecutionPlan(structured) {
  if (!structured || typeof structured !== "object") {
    return "아직 내부 실행계획이 없습니다.";
  }

  const internalPlan = structured.internal_execution_plan || {};
  const assignments = Array.isArray(internalPlan.team_assignments) ? internalPlan.team_assignments : [];
  const nextActions = Array.isArray(internalPlan.immediate_next_actions) ? internalPlan.immediate_next_actions : [];
  const lines = [];

  if (assignments.length > 0) {
    lines.push("팀 배정:");
    for (const item of assignments) {
      const member = item.team_member || "미배정";
      const responsibility = item.responsibility || "등록된 책임 없음";
      lines.push(`- ${member}: ${responsibility}`);
      if (item.reason) {
        lines.push(`  사유: ${item.reason}`);
      }
    }
  }

  if (nextActions.length > 0) {
    if (lines.length > 0) {
      lines.push("");
    }
    lines.push("즉시 진행할 업무:");
    for (const item of nextActions) {
      lines.push(`- ${item}`);
    }
  }

  return lines.join("\n").trim() || "아직 내부 실행계획이 없습니다.";
}

async function processDocument() {
  const file = documentInput.files?.[0];
  const profile = profileSelect.value;
  const systemPrompt = systemPromptInput.value.trim();
  const instruction = documentInstructionInput.value.trim();
  const teamContext = teamContextInput.value.trim();

  if (!file) {
    setStatus("먼저 문서를 선택하세요.");
    documentInput.focus();
    return;
  }

  setBusyState(true);
  documentMeta.textContent = `${file.name} 처리 중...`;
  documentExtractOutput.textContent = "텍스트 추출 중...";
  documentSummaryOutput.textContent = "요약 대기 중...";
  documentStructuredOutput.textContent = "구조화 분석 대기 중...";
  documentExecutionOutput.textContent = "내부 실행계획 대기 중...";
  setStatus(`${profile} 프로필로 ${file.name} 업로드 중...`);

  try {
    const arrayBuffer = await file.arrayBuffer();
    const fileDataBase64 = bytesToBase64(new Uint8Array(arrayBuffer));
    const response = await fetch("/api/process-document", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        profile,
        file_name: file.name,
        file_data_base64: fileDataBase64,
        system_prompt: systemPrompt,
        instruction,
        team_context: teamContext,
      }),
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "문서 처리에 실패했습니다.");
    }

    documentMeta.textContent =
      `${payload.file_name} 문서를 ${payload.profile} 프로필로 처리했습니다. ` +
      `${payload.extracted_char_count}자 추출. ` +
      formatRagStatus(payload.rag) +
      (payload.summary_source_truncated ? " MVP 제한으로 요약 입력 일부가 잘렸습니다." : "");
    documentExtractOutput.textContent = payload.extracted_text || "(빈 추출 텍스트)";
    documentSummaryOutput.textContent = payload.summary || "(빈 요약)";
    documentStructuredOutput.textContent = formatStructuredInsights(payload.structured);
    documentExecutionOutput.textContent = formatExecutionPlan(payload.structured);
    proposalOpsOutput.textContent = formatProposalOpsPlan(payload.proposal_ops);
    announcementAgentMeta.textContent = formatAnnouncementAgentMeta(payload.announcement_agent);
    renderRagDocuments(payload.rag || {});
    await loadIngestionState();
    setStatus(`${payload.profile} 프로필로 문서를 처리했습니다. ${formatRagStatus(payload.rag)}`);
  } catch (error) {
    const message = String(error.message || error);
    documentMeta.textContent = "문서 처리에 실패했습니다.";
    documentExtractOutput.textContent = message;
    documentSummaryOutput.textContent = message;
    documentStructuredOutput.textContent = message;
    documentExecutionOutput.textContent = message;
    setStatus("문서 요청에 실패했습니다.");
  } finally {
    setBusyState(false);
  }
}

async function runAnnouncementAgentBundle() {
  const files = Array.from(announcementFolderInput.files || []);
  const profile = profileSelect.value;
  const systemPrompt = systemPromptInput.value.trim();
  const baseInstruction = documentInstructionInput.value.trim();
  const feedbackInstruction = announcementFeedbackInput.value.trim();
  const instruction = feedbackInstruction
    ? `${baseInstruction}\n\n사용자 교정/확인사항:\n${feedbackInstruction}`.trim()
    : baseInstruction;
  const teamContext = teamContextInput.value.trim();

  if (files.length === 0) {
    setStatus("공고 파일 세트가 들어있는 폴더를 먼저 선택하세요.");
    announcementFolderInput.focus();
    return;
  }

  setBusyState(true);
  announcementFolderMeta.textContent = `${files.length}개 파일 처리 중...`;
  announcementAgentOutput.textContent = "공고 분석과 파일 생성을 실행 중입니다.";
  announcementDashboardOutput.textContent = "공고리스트 대시보드 갱신 중입니다.";
  setStatus(`공고 에이전트 실행 중: ${files.length}개 파일`);

  try {
    const encodedFiles = [];
    for (const file of files) {
      const arrayBuffer = await file.arrayBuffer();
      encodedFiles.push({
        file_name: file.name,
        relative_path: file.webkitRelativePath || file.name,
        file_data_base64: bytesToBase64(new Uint8Array(arrayBuffer)),
      });
    }
    const response = await fetch("/api/announcement-agent/run", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        profile,
        files: encodedFiles,
        system_prompt: systemPrompt,
        instruction,
        team_context: teamContext,
      }),
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "공고 에이전트 실행에 실패했습니다.");
    }

    const agent = payload.announcement_agent || {};
    lastAnnouncementAgentPayload = payload;
    announcementFolderMeta.textContent =
      `${payload.file_count || files.length}개 파일 처리 완료. 생성 폴더: ${agent.project_dir || "확인 필요"}`;
    announcementAgentOutput.textContent = formatAnnouncementAgentBundleResult(payload);
    announcementDashboardOutput.textContent = formatAnnouncementDashboard(agent.dashboard_stats);
    proposalOpsOutput.textContent = formatProposalOpsPlan(payload.proposal_ops);
    announcementAgentMeta.textContent = formatAnnouncementAgentMeta(agent);
    if (payload.structured) {
      documentStructuredOutput.textContent = formatStructuredInsights(payload.structured);
      documentExecutionOutput.textContent = formatExecutionPlan(payload.structured);
    }
    documentSummaryOutput.textContent = payload.summary || documentSummaryOutput.textContent;
    if (payload.rag) {
      renderRagDocuments(payload.rag);
    }
    await loadIngestionState();
    setStatus(`공고 에이전트 완료. ${formatRagStatus(payload.rag)}`);
  } catch (error) {
    const message = String(error.message || error);
    announcementFolderMeta.textContent = "공고 에이전트 실행 실패.";
    announcementAgentOutput.textContent = message;
    announcementDashboardOutput.textContent = message;
    setStatus("공고 에이전트 요청 실패.");
  } finally {
    setBusyState(false);
  }
}

async function saveAnnouncementFeedback() {
  const feedback = announcementFeedbackInput.value.trim();
  if (!feedback) {
    setStatus("저장할 피드백을 입력하세요.");
    announcementFeedbackInput.focus();
    return;
  }

  setBusyState(true);
  setStatus("공고 에이전트 피드백 저장 중...");
  try {
    const payload = lastAnnouncementAgentPayload || {};
    const response = await fetch("/api/announcement-agent/feedback", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        profile: profileSelect.value,
        feedback,
        primary_file_name: payload.primary_file_name || "",
        document_id: payload.rag?.indexed_document_id || 0,
        structured: payload.structured || {},
        announcement_agent: payload.announcement_agent || {},
      }),
    });
    const saved = await response.json();
    if (!response.ok) {
      throw new Error(saved.error || "피드백 저장에 실패했습니다.");
    }
    setStatus(`피드백 저장 완료: ${saved.feedback_path}`);
  } catch (error) {
    setStatus(String(error.message || error));
  } finally {
    setBusyState(false);
  }
}

function handleDocumentSelection() {
  const file = documentInput.files?.[0];
  if (!file) {
    documentMeta.textContent = "아직 처리한 문서가 없습니다.";
    return;
  }

  documentMeta.textContent = `선택한 파일: ${file.name}`;
  documentExtractOutput.textContent = "아직 추출 텍스트가 없습니다.";
  documentSummaryOutput.textContent = "아직 요약이 없습니다.";
  documentStructuredOutput.textContent = "아직 구조화 분석 결과가 없습니다.";
  documentExecutionOutput.textContent = "아직 내부 실행계획이 없습니다.";
}

function handleAnnouncementFolderSelection() {
  const files = Array.from(announcementFolderInput.files || []);
  if (files.length === 0) {
    announcementFolderMeta.textContent = "선택된 폴더가 없습니다.";
    return;
  }
  const folderName = files[0].webkitRelativePath
    ? files[0].webkitRelativePath.split("/")[0]
    : "선택한 파일 세트";
  const totalBytes = files.reduce((sum, file) => sum + file.size, 0);
  announcementFolderMeta.textContent =
    `${folderName}: ${files.length}개 파일, ${(totalBytes / 1024 / 1024).toFixed(2)} MB`;
  announcementAgentOutput.textContent =
    "실행 버튼을 누르면 PDF 공고 파일을 찾아 분석한 뒤 공고 폴더, 총괄장, 공고리스트가 생성됩니다.";
  announcementDashboardOutput.textContent = "실행 후 일자별, 부처별, 사업유형별, 사업분야별 집계가 표시됩니다.";
}

refreshRagButton.addEventListener("click", async () => {
  try {
    await loadRagDocuments();
    setStatus("RAG 문서를 새로고침했습니다.");
  } catch (error) {
    setStatus(String(error.message || error));
  }
});

refreshIngestionButton.addEventListener("click", async () => {
  try {
    await loadIngestionState();
    setStatus("수집 상태를 새로고침했습니다.");
  } catch (error) {
    setStatus(String(error.message || error));
  }
});

ingestionReviewList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-review-item-id]");
  if (!button) {
    return;
  }
  void updateIngestionReviewStatus(button.dataset.reviewItemId, button.dataset.reviewStatus);
});

for (const button of navButtons) {
  button.addEventListener("click", () => {
    switchView(button.dataset.targetView);
  });
}

ragDocumentList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (button) {
    void runRagDocumentAction(button.dataset.action, button.dataset.documentId);
    return;
  }
  const item = event.target.closest(".rag-document-item[data-document-id]");
  if (item) {
    void openRagDocument(item.dataset.documentId);
  }
});

ragDocumentList.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") {
    return;
  }
  const item = event.target.closest(".rag-document-item[data-document-id]");
  if (!item) {
    return;
  }
  event.preventDefault();
  void openRagDocument(item.dataset.documentId);
});

refreshProfilesButton.addEventListener("click", async () => {
  try {
    await loadProfiles();
  } catch (error) {
    setStatus(String(error.message || error));
  }
});

sendButton.addEventListener("click", () => {
  void sendMessage();
});

copyButton.addEventListener("click", () => {
  void copyAnswer();
});

processDocumentButton.addEventListener("click", () => {
  void processDocument();
});

runAnnouncementAgentButton.addEventListener("click", () => {
  void runAnnouncementAgentBundle();
});

saveAnnouncementFeedbackButton.addEventListener("click", () => {
  void saveAnnouncementFeedback();
});

saveProjectContextButton.addEventListener("click", () => {
  void saveProjectContext();
});

documentInput.addEventListener("change", () => {
  handleDocumentSelection();
});

announcementFolderInput.addEventListener("change", () => {
  handleAnnouncementFolderSelection();
});

copyExtractedButton.addEventListener("click", () => {
  void copyText(documentExtractOutput.textContent, "아직 추출 텍스트가 없습니다.", "추출 텍스트를 복사했습니다.");
});

copySummaryButton.addEventListener("click", () => {
  void copyText(documentSummaryOutput.textContent, "아직 요약이 없습니다.", "요약을 복사했습니다.");
});

copyStructuredButton.addEventListener("click", () => {
  void copyText(
    documentStructuredOutput.textContent,
    "아직 구조화 분석 결과가 없습니다.",
    "구조화 분석 결과를 복사했습니다."
  );
});

copyExecutionButton.addEventListener("click", () => {
  void copyText(
    documentExecutionOutput.textContent,
    "아직 내부 실행계획이 없습니다.",
    "내부 실행계획을 복사했습니다."
  );
});

copyProposalOpsButton.addEventListener("click", () => {
  void copyText(
    proposalOpsOutput.textContent,
    "아직 제안 운영 계획이 없습니다.",
    "제안 운영 계획을 복사했습니다."
  );
});

copyAnnouncementAgentButton.addEventListener("click", () => {
  void copyText(
    announcementAgentOutput.textContent,
    "아직 실행 결과가 없습니다.",
    "공고 에이전트 실행 결과가 복사되었습니다."
  );
});

messageInput.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    void sendMessage();
  }
});

void Promise.all([loadProfiles(), loadProjectContext(), loadRagDocuments(), loadIngestionState()]).catch((error) => {
  setStatus(String(error.message || error));
});
