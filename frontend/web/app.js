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

async function loadProfiles() {
  setStatus("Loading profiles...");
  const response = await fetch("/api/profiles");
  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.error || "Failed to load profiles.");
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

  setStatus(`Loaded ${payload.profiles.length} profiles.`);
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
    return "No retrieval sources yet.";
  }
  const filterSummary = formatAppliedRagFilters(rag.applied_filters);
  const lines = rag.sources
    .map((source) => {
      const score = typeof source.score === "number" ? source.score.toFixed(4) : "n/a";
      const metadata = [
        source.document_type ? `type=${source.document_type}` : "",
        source.title ? `title=${source.title}` : "",
        source.ministry ? `ministry=${source.ministry}` : "",
        source.agency ? `agency=${source.agency}` : "",
        source.rd_or_non_rd ? `rd=${source.rd_or_non_rd}` : "",
        source.business_type ? `business=${source.business_type}` : "",
      ]
        .filter(Boolean)
        .join(" | ");
      return `${source.file_name} #${source.chunk_index} score ${score}${metadata ? ` | ${metadata}` : ""}`;
    });
  if (filterSummary) {
    lines.push(`Filters: ${filterSummary}`);
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
  ragStats.textContent = `${payload.indexed_document_count || 0} documents, ${payload.indexed_chunk_count || 0} chunks`;
  ragDbPath.textContent = payload.db_path ? `DB: ${payload.db_path}` : "DB path unavailable.";
  ragDocumentList.innerHTML = "";

  if (documents.length === 0) {
    const empty = document.createElement("p");
    empty.className = "helper-text";
    empty.textContent = "No indexed RAG documents yet.";
    ragDocumentList.appendChild(empty);
    return;
  }

  for (const documentItem of documents) {
    const item = document.createElement("article");
    item.className = "rag-document-item";
    item.dataset.documentId = String(documentItem.id);
    item.tabIndex = 0;
    item.setAttribute("role", "button");
    item.setAttribute("aria-label", `Open ${documentItem.file_name || `document ${documentItem.id}`}`);

    const details = document.createElement("div");
    const title = document.createElement("h3");
    title.textContent = documentItem.title || documentItem.file_name || `Document ${documentItem.id}`;
    const summary = document.createElement("p");
    summary.textContent = [
      documentItem.document_type ? `type ${documentItem.document_type}` : "type unknown",
      documentItem.ministry ? `ministry ${documentItem.ministry}` : "",
      documentItem.agency ? `agency ${documentItem.agency}` : "",
      documentItem.business_type ? `business ${documentItem.business_type}` : "",
      documentItem.submission_deadline ? `deadline ${documentItem.submission_deadline}` : "",
    ]
      .filter(Boolean)
      .join(" | ");
    const meta = document.createElement("p");
    meta.textContent = [
      `ID ${documentItem.id}`,
      documentItem.file_name ? `file ${documentItem.file_name}` : "",
      `${documentItem.chunk_count || 0} chunks`,
      documentItem.embedding_profile ? `embedding ${documentItem.embedding_profile}` : "embedding unknown",
      documentItem.chat_profile ? `chat ${documentItem.chat_profile}` : "chat unknown",
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
    reindexButton.textContent = "Reindex";
    const viewButton = document.createElement("button");
    viewButton.className = "ghost-button";
    viewButton.type = "button";
    viewButton.dataset.action = "view";
    viewButton.dataset.documentId = String(documentItem.id);
    viewButton.textContent = "Open";
    const deleteButton = document.createElement("button");
    deleteButton.className = "ghost-button danger-button";
    deleteButton.type = "button";
    deleteButton.dataset.action = "delete";
    deleteButton.dataset.documentId = String(documentItem.id);
    deleteButton.textContent = "Delete";
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
    throw new Error(payload.error || "Failed to load RAG documents.");
  }
  renderRagDocuments(payload);
}

function renderIngestionState(payload) {
  const summary = payload.summary || {};
  const reviewItems = Array.isArray(payload.review_items) ? payload.review_items : [];
  ingestionStats.textContent = [
    `${summary.source_count || 0} sources`,
    `${summary.plan_count || 0} plans`,
    `${summary.job_count || 0} jobs`,
    `${summary.review_item_count || 0} review items`,
    `${summary.needs_review_count || 0} need review`,
    `${summary.approved_count || 0} approved`,
  ].join(" | ");
  ingestionReviewList.innerHTML = "";

  if (reviewItems.length === 0) {
    const empty = document.createElement("p");
    empty.className = "helper-text";
    empty.textContent = "No ingestion review items yet.";
    ingestionReviewList.appendChild(empty);
    return;
  }

  for (const item of reviewItems) {
    const row = document.createElement("article");
    row.className = "ingestion-review-item";
    const details = document.createElement("div");
    const title = document.createElement("h3");
    title.textContent = item.file_name || item.source_uri || `Review item ${item.id}`;
    const meta = document.createElement("p");
    meta.textContent = [
      `status ${item.review_status}`,
      item.document_id ? `document ${item.document_id}` : "",
      item.quality_score !== null && item.quality_score !== undefined ? `quality ${item.quality_score}` : "",
      item.source_uri ? `source ${item.source_uri}` : "",
    ]
      .filter(Boolean)
      .join(" | ");
    const notes = document.createElement("p");
    notes.textContent = item.notes || "No review notes.";
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
      button.textContent =
        status === "needs_review" ? "Needs Review" : status.charAt(0).toUpperCase() + status.slice(1);
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
    throw new Error(payload.error || "Failed to load ingestion state.");
  }
  renderIngestionState(payload);
}

async function updateIngestionReviewStatus(reviewItemId, reviewStatus) {
  setBusyState(true);
  setStatus(`Updating review item ${reviewItemId}...`);
  try {
    const response = await fetch("/api/ingestion/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        review_item_id: Number(reviewItemId),
        review_status: reviewStatus,
        notes: reviewStatus === "approved" ? "Approved from document dashboard." : "",
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Failed to update ingestion review item.");
    }
    renderIngestionState(payload);
    setStatus(`Review item ${reviewItemId} marked ${reviewStatus}.`);
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
    throw new Error(payload.error || "Failed to load project context.");
  }
  systemPromptInput.value = payload.system_prompt || "";
  documentInstructionInput.value = payload.instruction || "";
  teamContextInput.value = payload.team_context || "";
}

async function saveProjectContext() {
  setBusyState(true);
  setStatus("Saving project context...");
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
      throw new Error(payload.error || "Failed to save project context.");
    }
    systemPromptInput.value = payload.system_prompt || "";
    documentInstructionInput.value = payload.instruction || "";
    teamContextInput.value = payload.team_context || "";
    setStatus("Project context saved.");
  } catch (error) {
    setStatus(String(error.message || error));
  } finally {
    setBusyState(false);
  }
}

async function openRagDocument(documentId) {
  setStatus(`Opening RAG document ${documentId}...`);
  try {
    const response = await fetch(`/api/rag/document?document_id=${encodeURIComponent(documentId)}`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Failed to open RAG document.");
    }
    renderDocumentDetail(payload);
    setStatus(`Opened ${payload.file_name}.`);
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
  const extractedText = payload.extracted_text || chunkFallback || "(no stored text)";
  documentMeta.textContent = [
    payload.file_name || `Document ${payload.id}`,
    metadata.document_type ? `type ${metadata.document_type}` : "",
    metadata.ministry ? `ministry ${metadata.ministry}` : "",
    metadata.agency ? `agency ${metadata.agency}` : "",
    metadata.submission_deadline ? `deadline ${metadata.submission_deadline}` : "",
    payload.artifact_available ? "stored analysis available" : "showing stored chunks only",
  ]
    .filter(Boolean)
    .join(" | ");
  documentExtractOutput.textContent = extractedText;
  documentSummaryOutput.textContent = payload.summary || "(no stored summary)";
  documentStructuredOutput.textContent =
    structured && Object.keys(structured).length > 0
      ? formatStructuredInsights(structured)
      : "(no stored structured insights)";
  documentExecutionOutput.textContent =
    structured && Object.keys(structured).length > 0
      ? formatExecutionPlan(structured)
      : "(no stored internal execution plan)";
}

async function runRagDocumentAction(action, documentId) {
  if (action === "view") {
    await openRagDocument(documentId);
    return;
  }
  if (action === "delete" && !window.confirm(`Delete RAG document ${documentId}?`)) {
    return;
  }
  const endpoint = action === "delete" ? "/api/rag/delete" : "/api/rag/reindex";
  const body = { document_id: Number(documentId) };
  if (action === "reindex") {
    body.profile = profileSelect.value;
  }

  setBusyState(true);
  setStatus(`${action === "delete" ? "Deleting" : "Reindexing"} RAG document ${documentId}...`);
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "RAG document action failed.");
    }
    renderRagDocuments(payload);
    setStatus(`RAG document ${documentId} ${action === "delete" ? "deleted" : "reindexed"}.`);
  } catch (error) {
    setStatus(String(error.message || error));
  } finally {
    setBusyState(false);
  }
}

function formatRagStatus(rag) {
  if (!rag || typeof rag !== "object") {
    return "RAG status unavailable.";
  }
  if (rag.enabled) {
    const sourceCount = Array.isArray(rag.sources) ? rag.sources.length : 0;
    if (sourceCount > 0) {
      return `RAG used ${sourceCount} retrieved chunks via ${rag.embedding_profile}.`;
    }
    return `RAG indexed ${rag.indexed_chunk_count || 0} chunks via ${rag.embedding_profile}.`;
  }
  if (rag.error) {
    return `RAG not used: ${rag.error}`;
  }
  return rag.reason || "RAG not used yet.";
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
    setStatus("Type a message first.");
    messageInput.focus();
    return;
  }

  setBusyState(true);
  responseOutput.textContent = "Waiting for response...";
  setStatus(`Sending with ${profile}...`);

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
      throw new Error(payload.error || "Request failed.");
    }

    responseOutput.textContent = payload.answer || "(empty response)";
    ragSourceOutput.textContent = formatRagSources(payload.rag);
    setStatus(`Done with ${payload.profile}. ${formatRagStatus(payload.rag)}`);
  } catch (error) {
    responseOutput.textContent = String(error.message || error);
    setStatus("Request failed.");
  } finally {
    setBusyState(false);
  }
}

async function copyText(text, emptyFallbackMessage, successMessage) {
  if (!text || text === emptyFallbackMessage) {
    setStatus("Nothing to copy yet.");
    return;
  }
  await navigator.clipboard.writeText(text);
  setStatus(successMessage);
}

async function copyAnswer() {
  await copyText(responseOutput.textContent, "No response yet.", "Answer copied.");
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
    return "No structured insights yet.";
  }

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
    lines.push(`Title: ${overview.title}`);
  }
  if (overview.main_purpose) {
    lines.push(`Main purpose: ${overview.main_purpose}`);
  }
  if (overview.project_type) {
    lines.push(`Project type: ${overview.project_type}`);
  }
  if (overview.support_summary) {
    lines.push(`Support summary: ${overview.support_summary}`);
  }

  lines.push("");
  lines.push("Consortium requirements:");
  lines.push(`- Consortium required: ${consortium.consortium_required ? "Yes" : "No"}`);
  lines.push(`- Demand company required: ${consortium.demand_company_required ? "Yes" : "No"}`);
  if (Array.isArray(consortium.lead_org_allowed) && consortium.lead_org_allowed.length > 0) {
    lines.push(`- Lead org allowed: ${consortium.lead_org_allowed.join(", ")}`);
  }
  if (Array.isArray(consortium.partner_org_allowed) && consortium.partner_org_allowed.length > 0) {
    lines.push(`- Partner org allowed: ${consortium.partner_org_allowed.join(", ")}`);
  }
  lines.push(`- Subcontractor allowed: ${consortium.subcontractor_allowed ? "Yes" : "No"}`);
  if (Array.isArray(consortium.notes) && consortium.notes.length > 0) {
    lines.push("");
    lines.push("Consortium notes:");
    for (const note of consortium.notes) {
      lines.push(`- ${note}`);
    }
  }

  if (eligibility.length > 0) {
    lines.push("");
    lines.push("Eligibility by role:");
    for (const item of eligibility) {
      const entities = Array.isArray(item.eligible_entities) ? item.eligible_entities.join(", ") : "";
      lines.push(`- ${item.role || "Unknown role"}: ${entities || "No eligible entities listed"}`);
      if (Array.isArray(item.restrictions) && item.restrictions.length > 0) {
        lines.push(`  restrictions: ${item.restrictions.join("; ")}`);
      }
    }
  }

  if (Array.isArray(strategy.recommended_structure) && strategy.recommended_structure.length > 0) {
    lines.push("");
    lines.push("Recommended consortium strategy:");
    for (const item of strategy.recommended_structure) {
      lines.push(`- ${item}`);
    }
  }
  if (Array.isArray(strategy.recommended_role_rr) && strategy.recommended_role_rr.length > 0) {
    lines.push("");
    lines.push("Recommended role R&R:");
    for (const item of strategy.recommended_role_rr) {
      const roleLine = `${item.role || "Unknown role"} -> ${item.recommended_entity_type || "Unspecified entity"}`;
      lines.push(`- ${roleLine}`);
      if (Array.isArray(item.responsibilities) && item.responsibilities.length > 0) {
        lines.push(`  responsibilities: ${item.responsibilities.join("; ")}`);
      }
    }
  }
  if (Array.isArray(strategy.key_differentiators) && strategy.key_differentiators.length > 0) {
    lines.push("");
    lines.push("Key differentiators:");
    for (const item of strategy.key_differentiators) {
      lines.push(`- ${item}`);
    }
  }

  if (budget.total_amount || budget.matching_requirement || (Array.isArray(budget.by_year) && budget.by_year.length > 0)) {
    lines.push("");
    lines.push("Budget:");
    if (budget.total_amount) {
      lines.push(`- Total amount: ${budget.total_amount}`);
    }
    if (Array.isArray(budget.by_year) && budget.by_year.length > 0) {
      for (const item of budget.by_year) {
        lines.push(`- ${item.year || "Year"}: ${item.amount || "Amount not listed"}`);
      }
    }
    if (budget.matching_requirement) {
      lines.push(`- Matching requirement: ${budget.matching_requirement}`);
    }
    if (Array.isArray(budget.additional_info_needed) && budget.additional_info_needed.length > 0) {
      lines.push(`- Additional info needed: ${budget.additional_info_needed.join("; ")}`);
    }
  }

  if (documents.length > 0) {
    lines.push("");
    lines.push("Submission documents:");
    for (const item of documents) {
      const requiredFor = Array.isArray(item.required_for) ? item.required_for.join(", ") : "";
      const providedForm = item.provided_form ? "provided" : "external/unknown";
      lines.push(`- ${item.document_name || "Unnamed document"} | required for: ${requiredFor || "unspecified"} | form: ${providedForm}`);
      if (item.issuance_source) {
        lines.push(`  source: ${item.issuance_source}`);
      }
      if (item.notes) {
        lines.push(`  notes: ${item.notes}`);
      }
    }
  }

  lines.push("");
  lines.push(`Presentation required: ${presentation.required ? "Yes" : "No"}`);
  if (presentation.notes) {
    lines.push(`Presentation notes: ${presentation.notes}`);
  }

  if (schedule.announcement_date || schedule.start_at || schedule.end_at || schedule.submission_deadline) {
    lines.push("");
    lines.push("Application schedule:");
    if (schedule.announcement_date) {
      lines.push(`- Announcement date: ${schedule.announcement_date}`);
    }
    if (schedule.start_at) {
      lines.push(`- Start: ${schedule.start_at}`);
    }
    if (schedule.end_at) {
      lines.push(`- End: ${schedule.end_at}`);
    }
    if (schedule.submission_deadline) {
      lines.push(`- Submission deadline: ${schedule.submission_deadline}`);
    }
    if (Array.isArray(schedule.important_milestones) && schedule.important_milestones.length > 0) {
      for (const item of schedule.important_milestones) {
        lines.push(`- ${item.date || "Unknown date"}: ${item.label || "Milestone"}`);
      }
    }
  }

  if (channel.method || channel.portal_or_address || channel.notes) {
    lines.push("");
    lines.push("Submission channel:");
    if (channel.method) {
      lines.push(`- Method: ${channel.method}`);
    }
    if (channel.portal_or_address) {
      lines.push(`- Portal/address: ${channel.portal_or_address}`);
    }
    if (channel.notes) {
      lines.push(`- Notes: ${channel.notes}`);
    }
  }

  if (contacts.length > 0) {
    lines.push("");
    lines.push("Contacts:");
    for (const item of contacts) {
      const details = [item.organization, item.name, item.phone, item.email].filter(Boolean).join(" | ");
      lines.push(`- ${details || "Unknown contact"}`);
      if (item.topic) {
        lines.push(`  topic: ${item.topic}`);
      }
    }
  }

  if (Array.isArray(risks.compliance_risks) && risks.compliance_risks.length > 0) {
    lines.push("");
    lines.push("Compliance risks:");
    for (const item of risks.compliance_risks) {
      lines.push(`- ${item}`);
    }
  }
  if (Array.isArray(risks.missing_information) && risks.missing_information.length > 0) {
    lines.push("");
    lines.push("Missing information:");
    for (const item of risks.missing_information) {
      lines.push(`- ${item}`);
    }
  }
  if (Array.isArray(risks.go_no_go_checks) && risks.go_no_go_checks.length > 0) {
    lines.push("");
    lines.push("Go/No-Go checks:");
    for (const item of risks.go_no_go_checks) {
      lines.push(`- ${item}`);
    }
  }

  return lines.join("\n").trim() || "No structured insights yet.";
}

function formatExecutionPlan(structured) {
  if (!structured || typeof structured !== "object") {
    return "No internal execution plan yet.";
  }

  const internalPlan = structured.internal_execution_plan || {};
  const assignments = Array.isArray(internalPlan.team_assignments) ? internalPlan.team_assignments : [];
  const nextActions = Array.isArray(internalPlan.immediate_next_actions) ? internalPlan.immediate_next_actions : [];
  const lines = [];

  if (assignments.length > 0) {
    lines.push("Team assignments:");
    for (const item of assignments) {
      const member = item.team_member || "Unassigned";
      const responsibility = item.responsibility || "No responsibility listed";
      lines.push(`- ${member}: ${responsibility}`);
      if (item.reason) {
        lines.push(`  reason: ${item.reason}`);
      }
    }
  }

  if (nextActions.length > 0) {
    if (lines.length > 0) {
      lines.push("");
    }
    lines.push("Immediate next actions:");
    for (const item of nextActions) {
      lines.push(`- ${item}`);
    }
  }

  return lines.join("\n").trim() || "No internal execution plan yet.";
}

async function processDocument() {
  const file = documentInput.files?.[0];
  const profile = profileSelect.value;
  const systemPrompt = systemPromptInput.value.trim();
  const instruction = documentInstructionInput.value.trim();
  const teamContext = teamContextInput.value.trim();

  if (!file) {
    setStatus("Choose a document first.");
    documentInput.focus();
    return;
  }

  setBusyState(true);
  documentMeta.textContent = `Processing ${file.name}...`;
  documentExtractOutput.textContent = "Extracting text...";
  documentSummaryOutput.textContent = "Waiting for summary...";
  documentStructuredOutput.textContent = "Waiting for structured insights...";
  documentExecutionOutput.textContent = "Waiting for internal execution plan...";
  setStatus(`Uploading ${file.name} with ${profile}...`);

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
      throw new Error(payload.error || "Document processing failed.");
    }

    documentMeta.textContent =
      `${payload.file_name} processed with ${payload.profile}. ` +
      `${payload.extracted_char_count} chars extracted. ` +
      formatRagStatus(payload.rag) +
      (payload.summary_source_truncated ? " Summary source truncated for MVP." : "");
    documentExtractOutput.textContent = payload.extracted_text || "(empty extracted text)";
    documentSummaryOutput.textContent = payload.summary || "(empty summary)";
    documentStructuredOutput.textContent = formatStructuredInsights(payload.structured);
    documentExecutionOutput.textContent = formatExecutionPlan(payload.structured);
    renderRagDocuments(payload.rag || {});
    await loadIngestionState();
    setStatus(`Document processed with ${payload.profile}. ${formatRagStatus(payload.rag)}`);
  } catch (error) {
    const message = String(error.message || error);
    documentMeta.textContent = "Document processing failed.";
    documentExtractOutput.textContent = message;
    documentSummaryOutput.textContent = message;
    documentStructuredOutput.textContent = message;
    documentExecutionOutput.textContent = message;
    setStatus("Document request failed.");
  } finally {
    setBusyState(false);
  }
}

function handleDocumentSelection() {
  const file = documentInput.files?.[0];
  if (!file) {
    documentMeta.textContent = "No document processed yet.";
    return;
  }

  documentMeta.textContent = `Selected file: ${file.name}`;
  documentExtractOutput.textContent = "No extracted text yet.";
  documentSummaryOutput.textContent = "No summary yet.";
  documentStructuredOutput.textContent = "No structured insights yet.";
  documentExecutionOutput.textContent = "No internal execution plan yet.";
}

refreshRagButton.addEventListener("click", async () => {
  try {
    await loadRagDocuments();
    setStatus("RAG documents refreshed.");
  } catch (error) {
    setStatus(String(error.message || error));
  }
});

refreshIngestionButton.addEventListener("click", async () => {
  try {
    await loadIngestionState();
    setStatus("Ingestion state refreshed.");
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

saveProjectContextButton.addEventListener("click", () => {
  void saveProjectContext();
});

documentInput.addEventListener("change", () => {
  handleDocumentSelection();
});

copyExtractedButton.addEventListener("click", () => {
  void copyText(documentExtractOutput.textContent, "No extracted text yet.", "Extracted text copied.");
});

copySummaryButton.addEventListener("click", () => {
  void copyText(documentSummaryOutput.textContent, "No summary yet.", "Summary copied.");
});

copyStructuredButton.addEventListener("click", () => {
  void copyText(
    documentStructuredOutput.textContent,
    "No structured insights yet.",
    "Structured insights copied."
  );
});

copyExecutionButton.addEventListener("click", () => {
  void copyText(
    documentExecutionOutput.textContent,
    "No internal execution plan yet.",
    "Internal execution plan copied."
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
