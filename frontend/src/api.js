const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "https://email-forensics-platform-y8mc.onrender.com";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, options);

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API error ${res.status}: ${text}`);
  }

  return res;
}

export const api = {
  async uploadEmails(files) {
    const form = new FormData();

    for (const file of files) {
      form.append("files", file);
    }

    const res = await request("/api/emails/upload", {
      method: "POST",
      body: form,
    });

    return res.json();
  },

  async listThreads() {
    const res = await request("/api/threads");
    return res.json();
  },

  async getThread(threadId) {
    const res = await request(`/api/threads/${threadId}`);
    return res.json();
  },

  async summarizeThread(threadId) {
    const res = await request(`/api/threads/${threadId}/summarize`, {
      method: "POST",
    });

    return res.json();
  },

  async getHops(emailId) {
    const res = await request(`/api/geo/${emailId}/hops`);
    return res.json();
  },

  async generateReport(emailId) {
    const res = await request(`/api/reports/${emailId}/generate`, {
      method: "POST",
    });

    return res.json();
  },

  downloadUrl(reportId, format) {
    return `${API_BASE_URL}/api/reports/${reportId}/download/${format}`;
  },
};

export default api;