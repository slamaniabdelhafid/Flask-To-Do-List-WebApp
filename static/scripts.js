function toggleTask(id, checkbox) {
    fetch(`/toggle/${id}`, {
        method: "POST"
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            checkbox.closest(".task-card").classList.toggle("done");
        }
    });
}
