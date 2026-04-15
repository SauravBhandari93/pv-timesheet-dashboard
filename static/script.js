async function loadData() {
  const res = await fetch("/api/timesheets");
  const data = await res.json();

  const tbody = document.querySelector("#table tbody");
  tbody.innerHTML = "";

  data.forEach((row) => {
    const tr = document.createElement("tr");

    tr.innerHTML = `
            <td>${row.employee_id ? row.employee_id[1] : ""}</td>
            <td>${row.unit_amount}</td>
            <td>${row.name}</td>
            <td>${row.date}</td>
        `;

    tbody.appendChild(tr);
  });
}

async function refreshData() {
  await fetch("/api/cache/clear");
  loadData();
}

loadData();
