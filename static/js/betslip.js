let selections = [];

document.addEventListener("DOMContentLoaded", () => {

    const buttons = document.querySelectorAll(".odd-button");

    buttons.forEach(button => {

        button.addEventListener("click", () => {

            const selection = {
                matchId: button.dataset.match,
                home: button.dataset.home,
                away: button.dataset.away,
                market: button.dataset.market,
                outcome: button.dataset.outcome,
                price: parseFloat(button.dataset.price)
            };

            addSelection(selection);
        });

    });

    const stakeInput = document.getElementById("stake");

    stakeInput.addEventListener("input", updatePotentialWin);

    document
        .getElementById("place-bet-btn")
        .addEventListener("click", placeBet);
});


function addSelection(selection) {

    // Don't add the same selection twice
    const existing = selections.find(
        item =>
            item.matchId === selection.matchId &&
            item.market === selection.market &&
            item.outcome === selection.outcome
    );

    if (existing) {
        return;
    }

    selections.push(selection);

    renderBetSlip();
}


function removeSelection(index) {

    selections.splice(index, 1);

    renderBetSlip();
}


function renderBetSlip() {

    const container = document.getElementById("bets-container");

    container.innerHTML = "";

    if (selections.length === 0) {

        container.innerHTML =
            '<p id="empty-betslip">No selections yet.</p>';

        updatePotentialWin();

        return;
    }

    selections.forEach((selection, index) => {

        const item = document.createElement("div");

        item.className = "bet-selection";

        item.innerHTML = `
            <div>
                <strong>
                    ${selection.home}
                    vs
                    ${selection.away}
                </strong>

                <div>
                    ${selection.outcome}
                    @ ${selection.price.toFixed(2)}
                </div>
            </div>

            <button
                type="button"
                onclick="removeSelection(${index})"
            >
                ✕
            </button>
        `;

        container.appendChild(item);
    });

    updatePotentialWin();
}


function updatePotentialWin() {

    const stakeInput = document.getElementById("stake");

    const stake = parseFloat(stakeInput.value) || 0;

    let totalOdds = 1;

    selections.forEach(selection => {

        totalOdds *= selection.price;

    });

    const potentialWin = stake * totalOdds;

    document.getElementById("potential-win").textContent =
        `Potential win: ₹${potentialWin.toFixed(2)}`;
}


async function placeBet() {

    if (selections.length === 0) {

        alert("Please select an odd first.");

        return;
    }

    const stake =
        parseFloat(
            document.getElementById("stake").value
        ) || 0;

    if (stake <= 0) {

        alert("Please enter a valid stake.");

        return;
    }

    const button =
        document.getElementById("place-bet-btn");

    button.disabled = true;
    button.textContent = "Placing...";

    try {

        const response = await fetch("/bets/place", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                selections: selections,
                stake: stake
            })
        });

        const result = await response.json();

        if (!response.ok) {

            alert(
                result.message ||
                "Unable to place bet."
            );

            return;
        }

        alert(
            `Bet placed successfully!\n\n` +
            `Bet ID: ${result.bet_id}\n` +
            `Stake: ₹${result.stake.toFixed(2)}\n` +
            `Odds: ${result.total_odds.toFixed(2)}\n` +
            `Potential win: ₹${result.potential_win.toFixed(2)}\n` +
            `Balance: ₹${result.balance.toFixed(2)}`
        );

        // Clear selections
        selections = [];

        // Clear stake
        document.getElementById("stake").value = "";

        // Re-render bet slip
        renderBetSlip();

    } catch (error) {

        console.error("Bet placement error:", error);

        alert(
            "Could not connect to the server."
        );

    } finally {

        button.disabled = false;
        button.textContent = "Place Bet";
    }
}