async function fetchTickets() {
  const res = await fetch('/tickets');
  const tickets = await res.json();
  const tbody = document.querySelector('#ticketsTable tbody');
  tbody.innerHTML = '';
  tickets.forEach(t => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${t.id}</td><td>${t.title}</td><td>${t.status}</td><td>${t.priority || ''}</td><td>${t.assigned_team || ''}</td>`;
    tr.onclick = () => showDetail(t.id);
    tbody.appendChild(tr);
  });
}

async function showDetail(id) {
  const res = await fetch(`/tickets/${id}`);
  const t = await res.json();
  document.getElementById('detail').textContent = JSON.stringify(t, null, 2);
}

async function submitTicket() {
  const title = document.getElementById('title').value;
  const description = document.getElementById('desc').value;
  const res = await fetch('/tickets', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({title, description, source: 'web'})
  });
  const ticket = await res.json();
  await fetch(`/process/${ticket.id}`, {method: 'POST'});
  await fetchTickets();
  await showDetail(ticket.id);
}

fetchTickets();
