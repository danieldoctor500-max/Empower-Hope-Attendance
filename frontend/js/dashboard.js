(() => {
	const api = window.AttendanceAPI;
	const state = { user: null, page: new URLSearchParams(location.search).get("view") || "overview", sessions: [], classes: [], students: [] };
	const view = document.querySelector("#view");
	const titles = {
		overview: ["TODAY", "Overview"],
		attendance: ["RECORDS", "Attendance"],
		sessions: ["SCHEDULE", "Sessions"],
		classes: ["LEARNING GROUPS", "Classes"],
		people: ["DIRECTORY", "People"],
		reports: ["INSIGHTS", "Reports"],
		audit: ["SYSTEM HISTORY", "Audit log"],
		profile: ["ACCOUNT", "My profile"],
	};
	const adminRoles = ["ADMIN", "SUPER_ADMIN"];

	function escapeHtml(value) {
		return String(value ?? "").replace(/[&<>"']/g, (char) => ({
			"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
		})[char]);
	}

	function today() {
		const now = new Date();
		return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
	}

	function dateLabel(value = new Date()) {
		return new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" }).format(value);
	}

	function isAdmin() {
		return adminRoles.includes(state.user?.role);
	}

	function toast(message, isError = false) {
		const element = document.querySelector("#toast");
		element.textContent = message;
		element.classList.toggle("toast-error", isError);
		element.classList.add("toast-visible");
		window.setTimeout(() => element.classList.remove("toast-visible"), 3200);
	}

	function showLogin() {
		document.querySelector("#auth-screen").hidden = false;
		document.querySelector("#app-shell").hidden = true;
		toggleAuthMode("login");
	}

	function toggleAuthMode(mode) {
		const buttons = document.querySelectorAll(".auth-mode-button");
		const forms = {
			login: document.querySelector("#login-form"),
			signup: document.querySelector("#signup-form"),
		};
		buttons.forEach((button) => {
			const isActive = button.dataset.authMode === mode;
			button.classList.toggle("is-active", isActive);
			button.setAttribute("aria-selected", String(isActive));
		});
		Object.entries(forms).forEach(([key, form]) => {
			form.hidden = key !== mode;
		});
	}

	function showApp() {
		document.querySelector("#auth-screen").hidden = true;
		document.querySelector("#app-shell").hidden = false;
		const fullName = `${state.user.first_name} ${state.user.last_name}`;
		document.querySelector("#profile-name").textContent = fullName;
		document.querySelector("#profile-role").textContent = state.user.role.replaceAll("_", " ").toLowerCase();
		document.querySelector("#avatar").textContent = `${state.user.first_name[0]}${state.user.last_name[0]}`.toUpperCase();
		document.querySelector("#topbar-date").textContent = dateLabel();
		buildNavigation();
	}

	function buildNavigation() {
		const workspaceItems = [
			["overview", "◫", "Overview"],
		];
		if (state.user.role === "STUDENT") {
			workspaceItems.push(["classes", "▦", "My classes"], ["sessions", "◷", "Sessions"]);
		} else {
			workspaceItems.push(["attendance", "✓", "Attendance"], ["classes", "▦", "Classes"], ["sessions", "◷", "Sessions"]);
		}

		const managementItems = [];
		if (isAdmin()) managementItems.push(["people", "♙", "People"]);
		managementItems.push(["reports", "▤", state.user.role === "STUDENT" ? "My records" : "Reports"]);
		managementItems.push(["profile", "●", state.user.role === "STUDENT" ? "Profile" : "Account"]);
		if (isAdmin()) managementItems.push(["audit", "↻", "Audit log"]);

		const sections = [
			{ title: "Core operations", items: workspaceItems },
			{ title: managementItems.length > 0 ? "Administration" : null, items: managementItems },
		].filter((section) => section.items.length > 0);

		document.querySelector("#primary-nav").innerHTML = sections.map(({ title, items }) => `
			<div class="nav-group">
				${title ? `<p class="nav-label">${title}</p>` : ""}
				${items.map(([page, icon, label]) => `
					<button class="nav-item ${state.page === page ? "is-active" : ""}" type="button" data-page="${page}">
						<span class="nav-icon" aria-hidden="true">${icon}</span><span>${label}</span>
					</button>`).join("")}
			</div>`).join("");
	}

	function setTitle(page) {
		const [kicker, title] = titles[page] || titles.overview;
		document.querySelector("#page-kicker").textContent = kicker;
		document.querySelector("#page-title").textContent = title;
	}

	async function navigate(page) {
		if (state.user?.role === "STUDENT" && page === "attendance") page = "reports";
		if (!isAdmin() && ["people", "audit"].includes(page)) page = "overview";
		state.page = page;
		history.replaceState(null, "", page === "overview" ? "/" : `/?view=${encodeURIComponent(page)}`);
		buildNavigation();
		setTitle(page);
		view.innerHTML = '<div class="loading-state"><span class="loader"></span>Loading workspace</div>';
		try {
			const pages = {
				overview: renderOverview,
				attendance: renderAttendance,
				sessions: renderSessions,
				classes: renderClasses,
				people: renderPeople,
				reports: renderReports,
				audit: renderAudit,
				profile: renderProfile,
			};
			await (pages[page] || renderOverview)();
		} catch (error) {
			if (error.message.includes("authentication credentials") || error.message.includes("Not authenticated")) {
				localStorage.removeItem(api.tokenKey);
				state.user = null;
				showLogin();
				return;
			}
			view.innerHTML = `<div class="error-state"><span class="error-symbol">!</span><div><strong>Could not load this view</strong><p>${escapeHtml(error.message)}</p><button class="button button-secondary" type="button" data-retry="${page}">Try again</button></div></div>`;
		}
	}

	function metric(label, value, detail, accent = "") {
		return `<article class="metric ${accent}"><p>${label}</p><strong>${value}</strong><small>${detail}</small></article>`;
	}

	function statusPill(status) {
		if (!status) return '<span class="status-pill status-empty">Not marked</span>';
		return `<span class="status-pill status-${status.toLowerCase()}">${status.toLowerCase()}</span>`;
	}

	function sessionLabel(session) {
		return `${escapeHtml(session.name)} · ${escapeHtml(session.start_time.slice(0, 5))}–${escapeHtml(session.end_time.slice(0, 5))}`;
	}

	async function renderOverview() {
		const summary = await window.ReportFeature.summary();
		const sessions = await window.SessionFeature.list({ session_date: today() });
		state.sessions = sessions;
		const rows = sessions.length ? sessions.map((session) => `
			<tr><td><strong>${escapeHtml(session.name)}</strong><small>${escapeHtml(session.class_id ? `Class ${session.class_id}` : "Community session")}</small></td>
			<td>${escapeHtml(session.start_time.slice(0, 5))}–${escapeHtml(session.end_time.slice(0, 5))}</td>
			<td>${statusPill(session.status)}</td>
			<td>${session.status === "OPEN" && state.user.role !== "STUDENT" ? `<button class="text-button" data-attend="${session.id}">Take attendance →</button>` : ""}</td></tr>`).join("") : '<tr><td colspan="4" class="table-empty">Nothing scheduled today.</td></tr>';
		const studentOverview = state.user.role === "STUDENT" ? `
			<div class="student-spotlight">
				<div>
					<p class="eyebrow">STUDENT OVERVIEW</p>
					<h3>You’re in good shape this week.</h3>
				</div>
				<div class="student-spotlight-actions">
					<button class="button button-secondary" type="button" data-page="reports">View records</button>
					<button class="button button-primary" type="button" data-page="profile">My profile</button>
				</div>
			</div>` : "";
		view.innerHTML = `
			<div class="page-hero">
				<div class="page-hero-copy">
					<p class="eyebrow">COMMUNITY PULSE</p>
					<h3>Attendance is moving in the right direction.</h3>
				</div>
				<div class="page-hero-meta">
					<span class="info-chip">Live today</span>
					<span class="info-chip">${summary.present} present</span>
					<span class="info-chip">${summary.absent} absent</span>
				</div>
			</div>
			<div class="welcome-row"><div><p class="eyebrow">${escapeHtml(dateLabel())}</p><h2>Welcome, ${escapeHtml(state.user.first_name)}.</h2><p class="muted">Here is the attendance picture for today.</p></div>${state.user.role !== "STUDENT" ? '<button class="button button-primary" data-page="sessions">＋ <span>Schedule session</span></button>' : ""}</div>
			${studentOverview}
			<div class="metric-grid">${metric("Sessions today", summary.today_sessions, `${summary.open_sessions} currently open`, "metric-green")}${metric("Present", summary.present, "Including late arrivals", "metric-coral")}${metric("Absent", summary.absent, `${summary.excused} excused`, "metric-yellow")}${metric("Attendance rate", `${summary.attendance_rate}%`, `${summary.recorded} records submitted`, "metric-ink")}</div>
			<section class="section-block"><div class="section-heading"><div><p class="eyebrow">ON THE CALENDAR</p><h3>Today's sessions</h3></div><button class="text-button" data-page="sessions">View schedule →</button></div>
				<div class="table-wrap"><table><thead><tr><th>Session</th><th>Time</th><th>Status</th><th></th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
	}

	async function renderAttendance(selectedId = "") {
		const sessions = await window.SessionFeature.list({ session_date: today() });
		state.sessions = sessions;
		const options = sessions.map((session) => `<option value="${session.id}" ${String(session.id) === String(selectedId) ? "selected" : ""}>${sessionLabel(session)}${session.status !== "OPEN" ? ` · ${session.status.toLowerCase()}` : ""}</option>`).join("");
		view.innerHTML = `
			<div class="page-hero">
				<div class="page-hero-copy">
					<p class="eyebrow">CHECK-IN</p>
					<h3>Mark attendance for the current session.</h3>
				</div>
				<div class="page-hero-meta">
					<span class="info-chip">Live roster</span>
					<span class="info-chip">${sessions.length} sessions</span>
				</div>
			</div>
			<div class="page-intro"><div><p class="muted">Choose an open session to record attendance.</p></div></div>
			<section class="control-strip"><label class="field field-inline"><span>Session</span><select id="attendance-session" required><option value="">Select today's session</option>${options}</select></label><span class="inline-note" id="session-state"></span></section>
			<section id="roster-area" class="section-block"><div class="empty-panel">Select an open session to load its roster.</div></section>`;
		document.querySelector("#attendance-session").addEventListener("change", (event) => loadRoster(event.target.value));
		if (selectedId) await loadRoster(selectedId);
	}

	async function loadRoster(sessionId) {
		const area = document.querySelector("#roster-area");
		const session = state.sessions.find((item) => String(item.id) === String(sessionId));
		const stateLabel = document.querySelector("#session-state");
		if (!sessionId || !session) {
			area.innerHTML = '<div class="empty-panel">Select an open session to load its roster.</div>';
			stateLabel.textContent = "";
			return;
		}
		if (session.status !== "OPEN") {
			area.innerHTML = '<div class="empty-panel">This session is not open for attendance.</div>';
			stateLabel.textContent = session.status.toLowerCase();
			return;
		}
		stateLabel.textContent = "OPEN FOR MARKING";
		area.innerHTML = '<div class="loading-state"><span class="loader"></span>Loading roster</div>';
		const roster = await window.AttendanceFeature.roster(sessionId);
		if (!roster.length) {
			area.innerHTML = '<div class="empty-panel">No active students are enrolled in this session.</div>';
			return;
		}
		area.innerHTML = `<form id="attendance-form"><div class="section-heading roster-heading"><div><p class="eyebrow">${roster.length} STUDENTS</p><h3>${escapeHtml(session.name)}</h3></div><button class="button button-primary" type="submit">Save attendance</button></div>
			<div class="table-wrap"><table class="roster-table"><thead><tr><th>Student</th><th>Email</th><th>Attendance</th><th>Note</th></tr></thead><tbody>${roster.map((student) => `<tr data-student="${student.student_id}"><td><strong>${escapeHtml(student.first_name)} ${escapeHtml(student.last_name)}</strong></td><td>${escapeHtml(student.email)}</td><td><select class="attendance-status" aria-label="Attendance for ${escapeHtml(student.first_name)} ${escapeHtml(student.last_name)}"><option value="">Keep current</option>${["PRESENT", "ABSENT", "LATE", "EXCUSED"].map((status) => `<option value="${status}" ${student.status === status ? "selected" : ""}>${status.charAt(0) + status.slice(1).toLowerCase()}</option>`).join("")}</select><small>${statusPill(student.status)}</small></td><td><input class="attendance-note" type="text" maxlength="1000" value="${escapeHtml(student.notes || "")}" placeholder="Optional"></td></tr>`).join("")}</tbody></table></div>
			<div class="form-actions"><span class="muted">Only changed rows will be saved.</span><button class="button button-primary" type="submit">Save attendance</button></div></form>`;
		document.querySelector("#attendance-form").addEventListener("submit", async (event) => {
			event.preventDefault();
			const records = [...event.currentTarget.querySelectorAll("tbody tr")].flatMap((row) => {
				const status = row.querySelector(".attendance-status").value;
				if (!status) return [];
				return [{ student_id: Number(row.dataset.student), status, notes: row.querySelector(".attendance-note").value || null }];
			});
			if (!records.length) return toast("Choose a status for at least one student.", true);
			const button = event.currentTarget.querySelector("button[type=submit]");
			button.disabled = true;
			try {
				await window.AttendanceFeature.mark(sessionId, records);
				toast(`Saved ${records.length} attendance record${records.length === 1 ? "" : "s"}.`);
				await loadRoster(sessionId);
			} catch (error) {
				toast(error.message, true);
				button.disabled = false;
			}
		});
	}

	async function renderSessions() {
		const [sessions, classes] = await Promise.all([window.SessionFeature.list(), state.user.role === "STUDENT" ? Promise.resolve([]) : window.ClassFeature.list()]);
		state.sessions = sessions;
		state.classes = classes;
		const classOptions = classes.map((class_) => `<option value="${class_.id}">${escapeHtml(class_.name)}</option>`).join("");
		const form = state.user.role === "STUDENT" ? "" : `<form id="session-form" class="inline-form session-create-form">
			<label class="field"><span>Session name</span><input name="name" maxlength="150" placeholder="e.g. Morning gathering" required></label>
			<label class="field"><span>Date</span><input name="session_date" type="date" value="${today()}" required></label>
			<label class="field"><span>Starts</span><input name="start_time" type="time" value="08:00" required></label>
			<label class="field"><span>Ends</span><input name="end_time" type="time" value="09:00" required></label>
			${state.user.role !== "STUDENT" ? `<label class="field"><span>Class</span><select name="class_id"><option value="">Community session</option>${classOptions}</select></label>` : ""}
			<button class="button button-primary" type="submit">Create session</button>
		</form>`;
		const rows = sessions.map((session) => `<tr><td><strong>${escapeHtml(session.name)}</strong><small>${escapeHtml(session.session_date)} · ${escapeHtml(session.class_id ? `Class ${session.class_id}` : "Community session")}</small></td><td>${escapeHtml(session.start_time.slice(0, 5))}–${escapeHtml(session.end_time.slice(0, 5))}</td><td>${statusPill(session.status)}</td><td class="row-actions">${state.user.role !== "STUDENT" && (session.status === "SCHEDULED" || session.status === "CLOSED") ? `<button class="button button-small button-secondary" data-session-action="open" data-session-id="${session.id}">Open</button>` : ""}${state.user.role !== "STUDENT" && session.status === "OPEN" ? `<button class="button button-small button-secondary" data-session-action="close" data-session-id="${session.id}">Close</button><button class="text-button" data-attend="${session.id}">Attendance</button>` : ""}</td></tr>`).join("") || '<tr><td colspan="4" class="table-empty">No sessions have been scheduled.</td></tr>';
		view.innerHTML = `
			<div class="page-hero">
				<div class="page-hero-copy">
					<p class="eyebrow">SCHEDULE</p>
					<h3>Keep your learning calendar on track.</h3>
				</div>
				<div class="page-hero-meta">
					<span class="info-chip">${sessions.length} sessions</span>
					<span class="info-chip">${sessions.filter((item) => item.status === "OPEN").length} open</span>
				</div>
			</div>
			<div class="page-intro"><p class="muted">Create a session, open it when attendance begins, then close it when complete.</p></div>${form}<section class="section-block"><div class="section-heading"><div><p class="eyebrow">SCHEDULE</p><h3>All sessions</h3></div></div><div class="table-wrap"><table><thead><tr><th>Session</th><th>Time</th><th>Status</th><th></th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
		document.querySelector("#session-form")?.addEventListener("submit", createSession);
	}

	async function createSession(event) {
		event.preventDefault();
		const form = new FormData(event.currentTarget);
		const classId = form.get("class_id");
		const body = {
			name: form.get("name"),
			session_type: classId ? "CLASS" : "GENERAL",
			session_date: form.get("session_date"),
			start_time: form.get("start_time"),
			end_time: form.get("end_time"),
			class_id: classId ? Number(classId) : null,
		};
		try {
			await window.SessionFeature.create(body);
			toast("Session created.");
			await navigate("sessions");
		} catch (error) {
			toast(error.message, true);
		}
	}

	async function renderClasses() {
		const classes = await window.ClassFeature.list();
		if (!isAdmin()) {
			const classRows = classes.map((class_) => `<tr><td><strong>${escapeHtml(class_.name)}</strong><small>${escapeHtml(class_.description || "No description")}</small></td><td>${statusPill(class_.status)}</td></tr>`).join("") || '<tr><td colspan="2" class="table-empty">No classes are assigned to you.</td></tr>';
			view.innerHTML = `
				<div class="page-hero">
					<div class="page-hero-copy">
						<p class="eyebrow">STUDENT GROUPS</p>
						<h3>Your assigned learning groups.</h3>
					</div>
					<div class="page-hero-meta">
						<span class="info-chip">${classes.length} groups</span>
					</div>
				</div>
				<div class="page-intro"><p class="muted">Your assigned learning groups.</p></div><section class="section-block"><div class="table-wrap"><table><thead><tr><th>Class</th><th>Status</th></tr></thead><tbody>${classRows}</tbody></table></div></section>`;
			return;
		}
		const [students, staff] = await Promise.all([window.ClassFeature.students(), window.ClassFeature.staff()]);
		state.classes = classes;
		state.students = students;
		const rows = classes.map((class_) => `<tr><td><strong>${escapeHtml(class_.name)}</strong><small>${escapeHtml(class_.description || "No description")}</small></td><td>${statusPill(class_.status)}</td><td><form class="mini-form enroll-form" data-class-id="${class_.id}"><select name="student_id" aria-label="Student to enroll"><option value="">Enroll a student</option>${students.map((student) => `<option value="${student.id}">${escapeHtml(student.first_name)} ${escapeHtml(student.last_name)}</option>`).join("")}</select><button class="button button-small button-secondary" type="submit">Add</button></form></td></tr>`).join("") || '<tr><td colspan="3" class="table-empty">No classes yet. Create one to get started.</td></tr>';
		view.innerHTML = `
			<div class="page-hero">
				<div class="page-hero-copy">
					<p class="eyebrow">CLASS HUB</p>
					<h3>Build groups, assign staff, and keep rosters moving.</h3>
				</div>
				<div class="page-hero-meta">
					<span class="info-chip">${classes.length} classes</span>
					<span class="info-chip">${staff.length} staff</span>
				</div>
			</div>
			<div class="page-intro"><p class="muted">Organize students into learning groups and assign staff.</p></div>
			<div class="split-panels"><section class="form-panel"><p class="eyebrow">NEW GROUP</p><h3>Create a class</h3><form id="class-form" class="stack-form"><label class="field"><span>Class name</span><input name="name" maxlength="100" required placeholder="e.g. Hope learners"></label><label class="field"><span>Description</span><textarea name="description" rows="3" maxlength="500" placeholder="Optional details"></textarea></label><button class="button button-primary" type="submit">Create class</button></form></section>
			<section class="form-panel"><p class="eyebrow">STAFF ASSIGNMENT</p><h3>Assign a teacher</h3><form id="staff-form" class="stack-form"><label class="field"><span>Class</span><select name="class_id" required><option value="">Select class</option>${classes.map((item) => `<option value="${item.id}">${escapeHtml(item.name)}</option>`).join("")}</select></label><label class="field"><span>Staff member</span><select name="staff_id" required><option value="">Select staff</option>${staff.map((person) => `<option value="${person.id}">${escapeHtml(person.first_name)} ${escapeHtml(person.last_name)}</option>`).join("")}</select></label><button class="button button-primary" type="submit">Assign staff</button></form></section></div>
			<section class="section-block"><div class="section-heading"><div><p class="eyebrow">CLASS ROSTERS</p><h3>Classes and enrollment</h3></div></div><div class="table-wrap"><table><thead><tr><th>Class</th><th>Status</th><th>Enroll student</th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
		document.querySelector("#class-form").addEventListener("submit", createClass);
		document.querySelector("#staff-form").addEventListener("submit", assignStaff);
		document.querySelectorAll(".enroll-form").forEach((form) => form.addEventListener("submit", enrollStudent));
	}

	async function createClass(event) {
		event.preventDefault();
		const values = Object.fromEntries(new FormData(event.currentTarget));
		try {
			await window.ClassFeature.create(values);
			toast("Class created.");
			await navigate("classes");
		} catch (error) { toast(error.message, true); }
	}

	async function assignStaff(event) {
		event.preventDefault();
		const values = Object.fromEntries(new FormData(event.currentTarget));
		try {
			await window.ClassFeature.assignStaff(Number(values.class_id), Number(values.staff_id));
			toast("Staff assignment saved.");
		} catch (error) { toast(error.message, true); }
	}

	async function enrollStudent(event) {
		event.preventDefault();
		const studentId = new FormData(event.currentTarget).get("student_id");
		if (!studentId) return toast("Choose a student first.", true);
		try {
			await window.ClassFeature.enroll(Number(studentId), Number(event.currentTarget.dataset.classId));
			toast("Student enrolled.");
			event.currentTarget.reset();
		} catch (error) { toast(error.message, true); }
	}

	async function renderPeople() {
		const [users, classes, enrollments] = await Promise.all([
			window.UserFeature.list(),
			window.ClassFeature.list(),
			api.get("/enrollments"),
		]);
		const classNames = new Map(classes.map((class_) => [class_.id, class_.name]));
		const classOptions = classes.map((class_) => `<option value="${class_.id}">${escapeHtml(class_.name)}</option>`).join("");
		const rows = users.map((person) => {
			const personEnrollments = enrollments.filter((enrollment) => enrollment.student_id === person.id);
			const personClasses = personEnrollments.map((enrollment) => classNames.get(enrollment.class_id)).filter(Boolean);
			const classIds = personEnrollments.map((enrollment) => enrollment.class_id).join(",");
			return `<tr data-class-ids="${classIds}"><td><strong>${escapeHtml(person.first_name)} ${escapeHtml(person.last_name)}</strong><small>${escapeHtml(person.email)}</small></td><td>${escapeHtml(person.student_id || "—")}</td><td>${escapeHtml(personClasses.join(", ") || "—")}</td><td><form class="user-update-form" data-user-id="${person.id}"><select name="role" aria-label="Role for ${escapeHtml(person.email)}">${["STUDENT", "STAFF", "ADMIN", "SUPER_ADMIN"].map((role) => `<option value="${role}" ${person.role === role ? "selected" : ""}>${role.replaceAll("_", " ")}</option>`).join("")}</select><select name="status" aria-label="Status for ${escapeHtml(person.email)}">${["ACTIVE", "INACTIVE", "SUSPENDED"].map((status) => `<option value="${status}" ${person.status === status ? "selected" : ""}>${status.toLowerCase()}</option>`).join("")}</select><button class="button button-small button-secondary" type="submit">Save</button></form></td></tr>`;
		}).join("") || '<tr><td colspan="4" class="table-empty">No accounts found.</td></tr>';
		view.innerHTML = `
			<div class="page-hero">
				<div class="page-hero-copy">
					<p class="eyebrow">PEOPLE</p>
					<h3>Manage access, roles, and status.</h3>
				</div>
				<div class="page-hero-meta">
					<span class="info-chip">${users.length} accounts</span>
				</div>
			</div>
			<div class="page-intro"><p class="muted">Create, update, or deactivate administrator, staff, and student accounts.</p></div><section class="form-panel people-create"><p class="eyebrow">NEW ACCOUNT</p><h3>Add a person</h3><form id="person-form" class="inline-form"><label class="field"><span>First name</span><input name="first_name" required maxlength="100"></label><label class="field"><span>Last name</span><input name="last_name" required maxlength="100"></label><label class="field"><span>Email</span><input name="email" type="email" required maxlength="255"></label><label class="field"><span>Temporary password</span><input name="password" type="password" required minlength="8" maxlength="128" autocomplete="new-password"></label><label class="field"><span>Role</span><select name="role"><option value="STUDENT">Student</option><option value="STAFF">Staff</option><option value="ADMIN">Administrator</option></select></label><button class="button button-primary" type="submit">Create account</button></form></section><section class="section-block"><div class="section-heading"><div><p class="eyebrow">DIRECTORY</p><h3>People</h3></div><span class="count-label">${users.length} accounts</span></div><label class="field field-inline"><span>Filter by class</span><select id="people-class-filter"><option value="">All classes</option>${classOptions}</select></label><div id="people-table-wrap" class="table-wrap"><table><thead><tr><th>Person</th><th>Student ID</th><th>Class</th><th>Account access</th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
		document.querySelector("#person-form").addEventListener("submit", createPerson);
		document.querySelectorAll(".user-update-form").forEach((form) => form.addEventListener("submit", updatePerson));
		document.querySelector("#people-class-filter").addEventListener("change", (event) => {
			const classId = event.target.value;
			document.querySelectorAll("#people-table-wrap tbody tr[data-class-ids]").forEach((row) => {
				row.hidden = Boolean(classId) && !row.dataset.classIds.split(",").includes(classId);
			});
		});
	}

	async function updatePerson(event) {
		event.preventDefault();
		const values = Object.fromEntries(new FormData(event.currentTarget));
		values.is_active = values.status === "ACTIVE";
		try {
			await window.UserFeature.update(Number(event.currentTarget.dataset.userId), values);
			toast("Account updated.");
			await navigate("people");
		} catch (error) { toast(error.message, true); }
	}

	async function createPerson(event) {
		event.preventDefault();
		const values = Object.fromEntries(new FormData(event.currentTarget));
		try {
			await window.UserFeature.create(values);
			toast("Account created.");
			await navigate("people");
		} catch (error) { toast(error.message, true); }
	}

	async function renderReports() {
		const start = `${today().slice(0, 7)}-01`;
		view.innerHTML = `
			<div class="page-hero">
				<div class="page-hero-copy">
					<p class="eyebrow">REPORTING</p>
					<h3>Track participation and export the record.</h3>
				</div>
				<div class="page-hero-meta">
					<span class="info-chip">CSV ready</span>
					<span class="info-chip">Date range</span>
				</div>
			</div>
			<div class="page-intro"><p class="muted">Review attendance history and export a CSV for the selected date range.</p></div>
			<form id="report-form" class="control-strip report-controls"><label class="field field-inline"><span>From</span><input name="start_date" type="date" value="${start}" required></label><label class="field field-inline"><span>To</span><input name="end_date" type="date" value="${today()}" required></label>${isAdmin() ? `<label class="field field-inline"><span>Class</span><select name="class_id" id="report-class"><option value="">All classes</option></select></label>` : ""}<button class="button button-secondary" type="submit">Apply filters</button><button id="export-button" class="button button-primary" type="button">↓ <span>Export CSV</span></button></form><section id="report-results" class="section-block"><div class="loading-state"><span class="loader"></span>Loading report</div></section>`;
		if (isAdmin()) {
			const classes = await window.ClassFeature.list();
			document.querySelector("#report-class").innerHTML += classes.map((item) => `<option value="${item.id}">${escapeHtml(item.name)}</option>`).join("");
		}
		document.querySelector("#report-form").addEventListener("submit", (event) => { event.preventDefault(); loadReport(); });
		document.querySelector("#export-button").addEventListener("click", exportReport);
		await loadReport();
	}

	function reportQuery() {
		const values = Object.fromEntries(new FormData(document.querySelector("#report-form")));
		const params = new URLSearchParams({ start_date: values.start_date, end_date: values.end_date });
		if (values.class_id) params.set("class_id", values.class_id);
		return params.toString();
	}

	async function loadReport() {
		const results = document.querySelector("#report-results");
		results.innerHTML = '<div class="loading-state"><span class="loader"></span>Loading report</div>';
		try {
			const rows = await window.ReportFeature.attendance(Object.fromEntries(new URLSearchParams(reportQuery())));
			const body = rows.map((row) => `<tr><td>${escapeHtml(row.session_date)}</td><td><strong>${escapeHtml(row.student_name)}</strong><small>${escapeHtml(row.email)}</small></td><td>${escapeHtml(row.session_name)}</td><td>${escapeHtml(row.class_name || "Community")}</td><td>${statusPill(row.status)}</td><td>${escapeHtml(row.marked_by || "—")}</td></tr>`).join("") || '<tr><td colspan="6" class="table-empty">No attendance records in this range.</td></tr>';
			results.innerHTML = `<div class="section-heading"><div><p class="eyebrow">ATTENDANCE RECORDS</p><h3>Report results</h3></div><span class="count-label">${rows.length} records</span></div><div class="table-wrap"><table><thead><tr><th>Date</th><th>Student</th><th>Session</th><th>Class</th><th>Status</th><th>Marked by</th></tr></thead><tbody>${body}</tbody></table></div>`;
		} catch (error) {
			results.innerHTML = `<div class="empty-panel">${escapeHtml(error.message)}</div>`;
		}
	}

	async function exportReport() {
		try {
			await window.ReportFeature.exportAttendance(Object.fromEntries(new URLSearchParams(reportQuery())));
			toast("Report downloaded.");
		} catch (error) { toast(error.message, true); }
	}

	async function renderAudit() {
		const logs = await window.ReportFeature.auditLog();
		const rows = logs.map((log) => `<tr><td>${escapeHtml(new Date(log.created_at).toLocaleString())}</td><td><strong>${escapeHtml(log.actor || "System")}</strong><small>${escapeHtml(log.action)}</small></td><td>${escapeHtml(log.description || `${log.entity_type} ${log.entity_id || ""}`)}</td></tr>`).join("") || '<tr><td colspan="3" class="table-empty">No activity has been recorded.</td></tr>';
		view.innerHTML = `
			<div class="page-hero">
				<div class="page-hero-copy">
					<p class="eyebrow">SYSTEM HISTORY</p>
					<h3>Recent actions and change events.</h3>
				</div>
				<div class="page-hero-meta">
					<span class="info-chip">${logs.length} events</span>
				</div>
			</div>
			<div class="page-intro"><p class="muted">Recent changes made across the attendance system.</p></div><section class="section-block"><div class="table-wrap"><table><thead><tr><th>When</th><th>Who</th><th>Activity</th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
	}

	function renderProfile() {
		view.innerHTML = `
			<div class="page-hero">
				<div class="page-hero-copy">
					<p class="eyebrow">ACCOUNT</p>
					<h3>Manage your profile and sign-in details.</h3>
				</div>
				<div class="page-hero-meta">
					<span class="info-chip">${escapeHtml(state.user.role.replaceAll("_", " "))}</span>
				</div>
			</div>
			<div class="page-intro"><p class="muted">Your account details and sign-in security.</p></div>
			<section class="form-panel profile-panel">
				<p class="eyebrow">ACCOUNT</p>
				<h3>${escapeHtml(state.user.first_name)} ${escapeHtml(state.user.last_name)}</h3>
				<dl class="profile-details">
					${state.user.student_id ? `<div><dt>Student ID</dt><dd>${escapeHtml(state.user.student_id)}</dd></div>` : ""}
					<div><dt>Email address</dt><dd>${escapeHtml(state.user.email)}</dd></div>
					<div><dt>Account status</dt><dd>${statusPill(state.user.status)}</dd></div>
					<div><dt>Role</dt><dd>${escapeHtml(state.user.role.replaceAll("_", " "))}</dd></div>
				</dl>
			</section>
			<section class="form-panel password-panel"><p class="eyebrow">SIGN-IN SECURITY</p><h3>Change password</h3><form id="password-change-form" class="stack-form"><label class="field"><span>Current password</span><input name="current_password" type="password" autocomplete="current-password" required></label><label class="field"><span>New password</span><input name="new_password" type="password" minlength="8" maxlength="128" autocomplete="new-password" required></label><label class="field"><span>Confirm new password</span><input name="confirm_password" type="password" minlength="8" maxlength="128" autocomplete="new-password" required></label><button class="button button-primary" type="submit">Update password</button></form></section>`;
		document.querySelector("#password-change-form").addEventListener("submit", changePassword);
	}

	async function changePassword(event) {
		event.preventDefault();
		const values = Object.fromEntries(new FormData(event.currentTarget));
		if (values.new_password !== values.confirm_password) return toast("The new passwords do not match.", true);
		try {
			await api.post("/auth/change-password", { current_password: values.current_password, new_password: values.new_password });
			event.currentTarget.reset();
			toast("Password updated.");
		} catch (error) { toast(error.message, true); }
	}

	async function handleLogin(event) {
		event.preventDefault();
		const form = new FormData(event.currentTarget);
		const error = document.querySelector("#login-error");
		const button = event.currentTarget.querySelector("button[type=submit]");
		error.hidden = true;
		button.disabled = true;
		try {
			await window.AuthFeature.login(form.get("identifier"), form.get("password"));
			state.user = await window.AuthFeature.currentUser();
			showApp();
			state.page = state.user.role === "STUDENT" ? "profile" : state.page;
			await navigate(state.page);
			toast(`Welcome back, ${state.user.first_name}.`);
			document.querySelector("#signup-form").reset();
		} catch (requestError) {
			error.textContent = requestError.message;
			error.hidden = false;
			window.AuthFeature.logout();
		} finally {
			button.disabled = false;
		}
	}

	async function handleSignup(event) {
		event.preventDefault();
		const form = new FormData(event.currentTarget);
		const error = document.querySelector("#signup-error");
		const button = event.currentTarget.querySelector("button[type=submit]");
		error.hidden = true;
		button.disabled = true;
		try {
			const payload = {
				first_name: String(form.get("first_name") || "").trim(),
				last_name: String(form.get("last_name") || "").trim(),
				student_id: String(form.get("student_id") || "").trim(),
				email: String(form.get("email") || "").trim(),
				class_name: String(form.get("class_name") || ""),
				password: String(form.get("password") || ""),
			};
			const oauthToken = String(form.get("oauth_token") || "");
			if (oauthToken) {
				payload.oauth_token = oauthToken;
				await window.AuthFeature.registerWithOAuth(payload);
			} else {
				await window.AuthFeature.register(payload);
			}
			state.user = await window.AuthFeature.currentUser();
			showApp();
			state.page = state.user.role === "STUDENT" ? "profile" : "overview";
			await navigate(state.page);
			toast(`Welcome, ${state.user.first_name}! Your student account is ready.`);
			document.querySelector("#login-form").reset();
		} catch (requestError) {
			error.textContent = requestError.message;
			error.hidden = false;
			window.AuthFeature.logout();
		} finally {
			button.disabled = false;
		}
	}

	async function handleOAuthCallback() {
		const params = new URLSearchParams(location.hash.slice(1));
		if (!params.size) return false;
		history.replaceState(null, "", `${location.pathname}${location.search}`);
		const accessToken = params.get("oauth_access_token");
		if (accessToken) {
			window.AuthFeature.storeToken(accessToken);
			try {
				state.user = await window.AuthFeature.currentUser();
				showApp();
				state.page = state.user.role === "STUDENT" ? "profile" : "overview";
				await navigate(state.page);
				toast(`Welcome back, ${state.user.first_name}.`);
				return true;
			} catch {
				window.AuthFeature.logout();
			}
		}
		const handoffToken = params.get("oauth_signup_token");
		if (handoffToken) {
			const form = document.querySelector("#signup-form");
			form.elements.namedItem("oauth_token").value = handoffToken;
			form.elements.namedItem("first_name").value = params.get("first_name") || "";
			form.elements.namedItem("last_name").value = params.get("last_name") || "";
			const email = form.elements.namedItem("email");
			email.value = params.get("email") || "";
			email.readOnly = true;
			toggleAuthMode("signup");
			return true;
		}
		const oauthError = params.get("oauth_error");
		if (oauthError) {
			const messages = {
				google_not_configured: "Google sign-in is not configured yet.",
				apple_not_configured: "Apple sign-in is not configured yet.",
				unsupported_provider: "That sign-in provider is not supported.",
				verified_email_required: "The provider did not verify your email address.",
				student_account_required: "This email belongs to a non-student account. Sign in with your account credentials.",
				google_account_link_failed: "This Google account is already linked elsewhere.",
				apple_account_link_failed: "This Apple account is already linked elsewhere.",
				google_verification_failed: "Google sign-in could not be verified. Please try again.",
				apple_verification_failed: "Apple sign-in could not be verified. Please try again.",
			};
			const error = document.querySelector("#oauth-error");
			error.textContent = messages[oauthError] || "Social sign-in could not be completed. Please try again.";
			error.hidden = false;
		}
		return false;
	}

	async function boot() {
		document.querySelector("#login-form").addEventListener("submit", handleLogin);
		document.querySelector("#signup-form").addEventListener("submit", handleSignup);
		document.querySelectorAll(".auth-mode-button").forEach((button) => {
			button.addEventListener("click", () => toggleAuthMode(button.dataset.authMode));
		});
		document.querySelector("#logout-button").addEventListener("click", () => {
			window.AuthFeature.logout();
			state.user = null;
			showLogin();
			document.querySelector("#login-form").reset();
			document.querySelector("#signup-form").reset();
		});
		document.addEventListener("click", (event) => {
			const pageButton = event.target.closest("[data-page]");
			if (pageButton) navigate(pageButton.dataset.page);
			const attendButton = event.target.closest("[data-attend]");
			if (attendButton) {
				navigate("attendance").then(() => {
					const sessionId = attendButton.dataset.attend;
					document.querySelector("#attendance-session").value = sessionId;
					loadRoster(sessionId);
				});
			}
			const sessionAction = event.target.closest("[data-session-action]");
			if (sessionAction) {
				const action = sessionAction.dataset.sessionAction;
				const transition = action === "open" ? window.SessionFeature.open : window.SessionFeature.close;
				transition(sessionAction.dataset.sessionId).then(() => {
					toast(`Session ${action === "open" ? "opened" : "closed"}.`);
					navigate("sessions");
				}).catch((error) => toast(error.message, true));
			}
			const retryButton = event.target.closest("[data-retry]");
			if (retryButton) navigate(retryButton.dataset.retry);
		});
		if (await handleOAuthCallback()) return;
		const token = localStorage.getItem(api.tokenKey);
		if (!token) return showLogin();
		try {
			state.user = await window.AuthFeature.currentUser();
			showApp();
			await navigate(state.page);
		} catch {
			localStorage.removeItem(api.tokenKey);
			showLogin();
		}
	}

	document.addEventListener("DOMContentLoaded", boot);
})();
