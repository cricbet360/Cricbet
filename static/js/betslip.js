"use strict";


/* =========================================================
   BEX BET SLIP
========================================================= */

const betSlipState = [];


/* =========================================================
   ELEMENTS
========================================================= */

const overlay =
    document.getElementById("betslipOverlay");

const betslip =
    document.getElementById("betslip");

const closeButton =
    document.getElementById("closeBetslip");

const selectionsContainer =
    document.getElementById("betslipSelections");

const stakeInput =
    document.getElementById("stakeInput");

const potentialWinElement =
    document.getElementById("potentialWin");

const placeBetButton =
    document.getElementById("placeBetButton");

const betslipError =
    document.getElementById("betslipError");

const betslipCount =
    document.getElementById("betslipCount");

const mobileBetslipButton =
    document.getElementById("mobileBetslipButton");

const mobileBetslipCount =
    document.getElementById("mobileBetslipCount");


/* =========================================================
   OPEN BET SLIP
========================================================= */

function openBetSlip() {

    if (!overlay) {
        return;
    }

    overlay.classList.add("open");

    overlay.setAttribute(
        "aria-hidden",
        "false"
    );

    document.body.style.overflow = "hidden";

}


/* =========================================================
   CLOSE BET SLIP
========================================================= */

function closeBetSlip() {

    if (!overlay) {
        return;
    }

    overlay.classList.remove("open");

    overlay.setAttribute(
        "aria-hidden",
        "true"
    );

    document.body.style.overflow = "";

}


/* =========================================================
   SHOW ERROR
========================================================= */

function showError(message) {

    if (!betslipError) {
        return;
    }

    betslipError.textContent = message;

    betslipError.hidden = false;

}


/* =========================================================
   HIDE ERROR
========================================================= */

function hideError() {

    if (!betslipError) {
        return;
    }

    betslipError.textContent = "";

    betslipError.hidden = true;

}


/* =========================================================
   ADD / UPDATE SELECTION
========================================================= */

function addSelection(button) {

    const marketId =
        button.dataset.marketId;

    const selectionId =
        button.dataset.selectionId;

    const runnerName =
        button.dataset.runnerName;

    const side =
        button.dataset.side;

    const price =
        parseFloat(button.dataset.price);


    if (!marketId) {
        showError("Market ID is missing.");
        return;
    }

    if (!selectionId) {
        showError("Selection ID is missing.");
        return;
    }

    if (!side) {
        showError("Bet side is missing.");
        return;
    }

    if (!Number.isFinite(price) || price <= 0) {
        showError("Selected odds are unavailable.");
        return;
    }


    hideError();


    /*
       Same market + same selection:

       Clicking BACK after LAY
       changes the selection to BACK.

       Clicking the same button again
       removes it.
    */

    const existingIndex =
        betSlipState.findIndex(
            item =>
                String(item.marketId) === String(marketId) &&
                String(item.selectionId) === String(selectionId)
        );


    if (existingIndex !== -1) {

        const existing =
            betSlipState[existingIndex];


        if (existing.side === side) {

            betSlipState.splice(
                existingIndex,
                1
            );

        } else {

            betSlipState[existingIndex] = {

                marketId,
                selectionId,
                runnerName,
                side,
                price

            };

        }

    } else {

        betSlipState.push({

            marketId,
            selectionId,
            runnerName,
            side,
            price

        });

    }


    renderBetSlip();

    openBetSlip();

}


/* =========================================================
   REMOVE SELECTION
========================================================= */

function removeSelection(
    marketId,
    selectionId
) {

    const index =
        betSlipState.findIndex(
            item =>
                String(item.marketId) === String(marketId) &&
                String(item.selectionId) === String(selectionId)
        );


    if (index !== -1) {

        betSlipState.splice(
            index,
            1
        );

    }


    renderBetSlip();

}


/* =========================================================
   CALCULATE TOTAL ODDS
========================================================= */

function calculateTotalOdds() {

    if (betSlipState.length === 0) {
        return 1;
    }


    return betSlipState.reduce(
        (total, selection) => {

            return total * Number(
                selection.price
            );

        },
        1
    );

}


/* =========================================================
   CALCULATE POTENTIAL WIN
========================================================= */

function calculatePotentialWin() {

    const stake =
        parseFloat(
            stakeInput.value
        );


    if (
        !Number.isFinite(stake) ||
        stake <= 0 ||
        betSlipState.length === 0
    ) {

        return 0;

    }


    return (
        stake *
        calculateTotalOdds()
    );

}


/* =========================================================
   UPDATE POTENTIAL WIN
========================================================= */

function updatePotentialWin() {

    const totalOdds =
        calculateTotalOdds();

    const potentialWin =
        calculatePotentialWin();


    if (potentialWinElement) {

        potentialWinElement.textContent =
            "₹" +
            potentialWin.toFixed(2);

    }


    if (placeBetButton) {

        placeBetButton.disabled =
            betSlipState.length === 0 ||
            potentialWin <= 0;

    }


    return {
        totalOdds,
        potentialWin
    };

}


/* =========================================================
   RENDER BET SLIP
========================================================= */

function renderBetSlip() {

    if (!selectionsContainer) {
        return;
    }


    const count =
        betSlipState.length;


    if (betslipCount) {

        if (count === 0) {

            betslipCount.textContent =
                "No selections";

        } else {

            betslipCount.textContent =
                count +
                (
                    count === 1
                        ? " selection"
                        : " selections"
                );

        }

    }


    if (mobileBetslipCount) {

        mobileBetslipCount.textContent =
            String(count);

    }


    if (count === 0) {

        selectionsContainer.innerHTML = `

            <div class="no-selections">

                <div class="no-selection-icon">
                    🎟️
                </div>

                <p>
                    Select a BACK or LAY price
                    to add a bet.
                </p>

            </div>

        `;

        updatePotentialWin();

        return;
    }


    let html = "";


    betSlipState.forEach(
        selection => {

            const sideClass =
                selection.side === "BACK"
                    ? "back"
                    : "lay";


            html += `

                <div
                    class="slip-item"
                    data-market-id="${escapeHtml(selection.marketId)}"
                    data-selection-id="${escapeHtml(selection.selectionId)}"
                >

                    <div class="slip-item-top">

                        <div class="slip-item-name">
                            ${escapeHtml(selection.runnerName)}
                        </div>

                        <button
                            type="button"
                            class="slip-item-remove"
                            data-remove-market="${escapeHtml(selection.marketId)}"
                            data-remove-selection="${escapeHtml(selection.selectionId)}"
                            aria-label="Remove selection"
                        >
                            ×
                        </button>

                    </div>


                    <div class="slip-item-meta">

                        <span
                            class="slip-side ${sideClass}"
                        >
                            ${escapeHtml(selection.side)}
                        </span>

                        <span class="slip-price">
                            ${Number(selection.price).toFixed(2)}
                        </span>

                    </div>


                    <div class="slip-market">
                        Market ID:
                        ${escapeHtml(selection.marketId)}
                    </div>

                </div>

            `;

        }
    );


    selectionsContainer.innerHTML =
        html;


    updatePotentialWin();

}


/* =========================================================
   HTML ESCAPE
========================================================= */

function escapeHtml(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");

}


/* =========================================================
   CLICK HANDLER FOR ODDS
========================================================= */

document.addEventListener(
    "click",
    function(event) {

        const button =
            event.target.closest(
                ".odd-button"
            );


        if (!button) {
            return;
        }


        if (button.disabled) {
            return;
        }


        addSelection(button);

    }
);


/* =========================================================
   REMOVE BUTTON
========================================================= */

document.addEventListener(
    "click",
    function(event) {

        const button =
            event.target.closest(
                ".slip-item-remove"
            );


        if (!button) {
            return;
        }


        const marketId =
            button.dataset.removeMarket;

        const selectionId =
            button.dataset.removeSelection;


        removeSelection(
            marketId,
            selectionId
        );

    }
);


/* =========================================================
   CLOSE BUTTON
========================================================= */

if (closeButton) {

    closeButton.addEventListener(
        "click",
        closeBetSlip
    );

}


/* =========================================================
   CLICK OUTSIDE
========================================================= */

if (overlay) {

    overlay.addEventListener(
        "click",
        function(event) {

            if (
                event.target === overlay
            ) {

                closeBetSlip();

            }

        }
    );

}


/* =========================================================
   MOBILE BET SLIP BUTTON
========================================================= */

if (mobileBetslipButton) {

    mobileBetslipButton.addEventListener(
        "click",
        openBetSlip
    );

}


/* =========================================================
   STAKE
========================================================= */

if (stakeInput) {

    stakeInput.addEventListener(
        "input",
        function() {

            hideError();

            updatePotentialWin();

        }
    );

}


/* =========================================================
   ESCAPE KEY
========================================================= */

document.addEventListener(
    "keydown",
    function(event) {

        if (event.key === "Escape") {

            closeBetSlip();

        }

    }
);


/* =========================================================
   PLACE BET
========================================================= */

if (placeBetButton) {

    placeBetButton.addEventListener(
        "click",
        async function() {

            hideError();


            if (betSlipState.length === 0) {

                showError(
                    "Please select a bet first."
                );

                return;

            }


            const stake =
                parseFloat(
                    stakeInput.value
                );


            if (
                !Number.isFinite(stake) ||
                stake <= 0
            ) {

                showError(
                    "Please enter a valid stake."
                );

                stakeInput.focus();

                return;

            }


            const totalOdds =
                calculateTotalOdds();


            placeBetButton.disabled = true;

            placeBetButton.textContent =
                "Placing Bet...";


            try {

                const response =
                    await fetch(
                        "/bets/place",
                        {

                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json",

                                "Accept":
                                    "application/json"
                            },

                            credentials:
                                "same-origin",

                            body: JSON.stringify({

                                selections:
                                    betSlipState.map(
                                        selection => ({

                                            marketId:
                                                selection.marketId,

                                            selectionId:
                                                selection.selectionId,

                                            side:
                                                selection.side

                                        })
                                    ),

                                stake:
                                    stake

                            })

                        }
                    );


                const result =
                    await response.json()
                        .catch(
                            () => ({})
                        );


                if (!response.ok) {

                    throw new Error(
                        result.message ||
                        "Could not place bet."
                    );

                }


                if (
                    !result.success
                ) {

                    throw new Error(
                        result.message ||
                        "Could not place bet."
                    );

                }


                /*
                    Successful bet
                */

                alert(
                    "Bet placed successfully.\n\n" +
                    "Bet ID: " +
                    result.bet_id +
                    "\n" +
                    "Odds: " +
                    Number(
                        result.total_odds
                    ).toFixed(2) +
                    "\n" +
                    "Potential win: ₹" +
                    Number(
                        result.potential_win
                    ).toFixed(2)
                );


                betSlipState.length = 0;

                stakeInput.value = "";

                renderBetSlip();

                closeBetSlip();


                /*
                    Refresh balance and
                    dashboard data.
                */

                window.location.reload();


            } catch (error) {

                console.error(
                    "Place bet error:",
                    error
                );


                showError(
                    error.message ||
                    "Could not place bet."
                );

            } finally {

                placeBetButton.textContent =
                    "Place Bet";


                updatePotentialWin();

            }

        }
    );

}


/* =========================================================
   INITIAL RENDER
========================================================= */

renderBetSlip();