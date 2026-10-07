(() => {
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

	function statusPill(status) {
		if (!status) return '<span class="status-pill status-empty">Not marked</span>';
		return `<span class="status-pill status-${escapeHtml(status.toLowerCase())}">${escapeHtml(status.toLowerCase())}</span>`;
	}

	window.AttendanceUtils = { escapeHtml, today, dateLabel, statusPill };
})();
