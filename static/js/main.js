// static/js/main.js
function editTransaction(index) {
    const modal = document.getElementById('editModal');
    const form = document.getElementById('editForm');

    // Set the form action URL
    form.action = `/edit_transaction/${index}`;

    // Get the transaction data from the table
    const row = document.querySelectorAll('table tbody tr')[index];
    const amount = row.children[2].textContent.split(' ')[1].replace(',', '');
    const name = row.children[3].textContent;
    const description = row.children[4].textContent;

    // Set the form values
    form.querySelector('[name="amount"]').value = parseFloat(amount);
    form.querySelector('[name="name"]').value = name;
    form.querySelector('[name="description"]').value = description;

    // Show the modal
    modal.classList.remove('hidden');
}

function closeEditModal() {
    const modal = document.getElementById('editModal');
    modal.classList.add('hidden');
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('editModal');
    if (event.target == modal) {
        closeEditModal();
    }
}