COORDS_COPY = """if (window.location.href.includes('game.php?')) {
    function add_copy_on_page() {
        let primary_coords = document.querySelector("#menu_row2 > td:nth-child(4) > b")
        primary_coords.onclick = function () {
            navigator.clipboard.writeText(primary_coords.textContent.slice(1, 8));
        }
        primary_coords.style.cursor = "pointer";
        primary_coords.dataset.title = "Click to copy";
        primary_coords.classList.add("tooltip-delayed");

        if (window.location.href.includes('info_village')) {
            let secondary_coords = document.querySelector(
                "#content_value > table > tbody > tr > td:nth-child(1) > table:nth-child(1) > tbody > tr:nth-child(3) > td:nth-child(2)"
            )
            secondary_coords.onclick = function () {
                navigator.clipboard.writeText(secondary_coords.textContent);
            }
            secondary_coords.style.cursor = "pointer";
            secondary_coords.dataset.title = "Click to copy";
            secondary_coords.classList.add("tooltip-delayed");
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        add_copy_on_page();
    });
    
}
"""
