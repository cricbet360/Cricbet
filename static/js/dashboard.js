"use strict";


let allMatches = [];
let currentFilter = "all";


/* =========================================================
   CONFIGURATION
========================================================= */

/*
 * WhatsApp number:
 *
 * India country code = 91
 * Your number = 8895898319
 *
 * Do NOT use +, spaces or hyphens.
 */

const WHATSAPP_NUMBER = "918895898319";


/* =========================================================
   HELPERS
========================================================= */

function escapeHtml(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function isLive(match) {

    if (!match) {
        return false;
    }

    const value =
        match.in_play ??
        match.inPlay;

    return (
        value === true ||
        value === 1 ||
        value === "1" ||
        value === "true" ||
        value === "True"
    );
}


function formatDate(value) {

    if (!value) {
        return "";
    }

    try {

        const date = new Date(value);

        if (
            Number.isNaN(
                date.getTime()
            )
        ) {
            return String(value);
        }

        return date.toLocaleString(
            "en-IN",
            {
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit"
            }
        );

    } catch {

        return String(value);

    }
}


/* =========================================================
   WHATSAPP
========================================================= */

function openWhatsApp(message) {

    if (!WHATSAPP_NUMBER) {

        console.error(
            "WhatsApp number is not configured."
        );

        return;
    }


    const url =
        `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(message)}`;


    console.log(
        "Opening WhatsApp:",
        url
    );


    window.open(
        url,
        "_blank",
        "noopener,noreferrer"
    );
}


/* =========================================================
   DEPOSIT
========================================================= */

function openDepositWhatsApp() {

    openWhatsApp(
        "Hello, I want to make a deposit in CricBet."
    );

}


/* =========================================================
   WITHDRAW
========================================================= */

function openWithdrawWhatsApp() {

    openWhatsApp(
        "Hello, I want to make a withdrawal from CricBet."
    );

}


/* =========================================================
   LOAD MATCHES
========================================================= */

async function loadMatches() {

    const container =
        document.getElementById("matches");


    if (!container) {
        return;
    }


    if (!allMatches.length) {

        container.innerHTML = `

            <div class="empty-state">

                <div class="empty-state-icon">
                    🏏
                </div>

                <div class="empty-state-title">
                    Loading cricket matches...
                </div>

                <div class="empty-state-text">
                    Fetching live cricket data.
                </div>

            </div>

        `;

    }


    try {

        const response =
            await fetch(
                "/api/cricket/matches",
                {
                    method: "GET",
                    credentials: "same-origin",
                    cache: "no-store",
                    headers: {
                        "Accept": "application/json"
                    }
                }
            );


        let payload = null;


        try {

            payload =
                await response.json();

        } catch {

            throw new Error(
                "Server returned invalid JSON."
            );

        }


        if (!response.ok) {

            throw new Error(
                payload?.error ||
                payload?.detail ||
                "Unable to load cricket matches."
            );

        }


        if (
            payload.success !== true
        ) {

            throw new Error(
                payload.error ||
                "Cricket API request failed."
            );

        }


        if (
            !Array.isArray(
                payload.matches
            )
        ) {

            throw new Error(
                "Invalid matches response."
            );

        }


        allMatches =
            payload.matches;


        renderMatches();


    } catch (error) {

        console.error(
            "CRICKET MATCH ERROR:",
            error
        );


        if (!allMatches.length) {

            container.innerHTML = `

                <div class="empty-state">

                    <div class="empty-state-icon">
                        ⚠️
                    </div>

                    <div class="empty-state-title">
                        Unable to load cricket data
                    </div>

                    <div class="empty-state-text">
                        ${escapeHtml(
                            error.message
                        )}
                    </div>

                    <button
                        type="button"
                        class="retry-matches-button"
                        onclick="loadMatches()"
                    >
                        RETRY
                    </button>

                </div>

            `;

        }

    }

}


/* =========================================================
   FILTER
========================================================= */

function setFilter(filter) {

    currentFilter =
        filter;


    document
        .querySelectorAll(
            ".sport-filter"
        )
        .forEach(button => {

            button.classList.toggle(
                "active",
                button.dataset.filter === filter
            );

        });


    renderMatches();

}


/* =========================================================
   RENDER MATCHES
========================================================= */

function renderMatches() {

    const container =
        document.getElementById(
            "matches"
        );


    if (!container) {
        return;
    }


    let matches =
        [...allMatches];


    if (
        currentFilter === "live"
    ) {

        matches =
            matches.filter(
                match => isLive(match)
            );

    }


    if (
        currentFilter === "upcoming"
    ) {

        matches =
            matches.filter(
                match => !isLive(match)
            );

    }


    if (!matches.length) {

        container.innerHTML = `

            <div class="empty-state">

                <div class="empty-state-icon">
                    🏏
                </div>

                <div class="empty-state-title">
                    No cricket matches
                </div>

                <div class="empty-state-text">
                    No matches are currently available for this filter.
                </div>

            </div>

        `;

        return;

    }


    container.innerHTML =
        matches
            .map(
                match =>
                    createMatchRow(match)
            )
            .join("");

}


/* =========================================================
   MATCH ROW
========================================================= */

function createMatchRow(match) {

    const gameId =
        match.game_id ??
        match.gameId ??
        "";


    const marketId =
        match.market_id ??
        match.marketId ??
        "";


    const eventName =
        match.event_name ??
        match.eventName ??
        "Cricket Match";


    const eventTime =
        match.event_time ??
        match.eventTime ??
        "";


    const team1 =
        match.team1 ??
        match.runnerName1 ??
        "Team 1";


    const team2 =
        match.team2 ??
        match.runnerName2 ??
        "Team 2";


    const team3 =
        match.team3 ??
        match.runnerName3 ??
        "The Draw";


    const live =
        isLive(match);


    return `

        <div
            class="sportsbook-match-row"
            data-game-id="${escapeHtml(gameId)}"
            data-market-id="${escapeHtml(marketId)}"
        >

            <div class="match-information">

                <div class="match-status-line">

                    ${
                        live
                            ? `
                                <span class="live-dot"></span>

                                <span class="match-status live-status">
                                    LIVE
                                </span>
                              `
                            : `
                                <span class="match-status upcoming-status">
                                    UPCOMING
                                </span>
                              `
                    }

                    <span class="match-time">
                        ${escapeHtml(
                            formatDate(eventTime)
                        )}
                    </span>

                </div>


                <div class="match-name">
                    ${escapeHtml(eventName)}
                </div>


                <div class="team-names">

                    <div class="team-name">
                        ${escapeHtml(team1)}
                    </div>

                    <div class="team-name">
                        ${escapeHtml(team2)}
                    </div>

                    ${
                        team3 &&
                        team3 !== "The Draw"
                            ? `
                                <div class="team-name">
                                    ${escapeHtml(team3)}
                                </div>
                              `
                            : ""
                    }

                </div>


                <div class="match-league">
                    Cricket
                </div>

            </div>


            <button
                type="button"
                class="odds-cell odds-team-1"
                disabled
                title="${escapeHtml(team1)}"
            >
                <span class="odds-empty">
                    -
                </span>
            </button>


            <button
                type="button"
                class="odds-cell odds-team-2"
                disabled
                title="${escapeHtml(team2)}"
            >
                <span class="odds-empty">
                    -
                </span>
            </button>


            <button
                type="button"
                class="odds-cell odds-draw"
                disabled
                title="${escapeHtml(team3)}"
            >
                <span class="odds-empty">
                    -
                </span>
            </button>


            <div class="match-action">

                <a
                    class="view-match-button"
                    href="/match/${encodeURIComponent(gameId)}"
                >
                    <span>→</span>
                    VIEW MATCH
                </a>

            </div>

        </div>

    `;

}


/* =========================================================
   BALANCE
========================================================= */

async function loadBalance() {

    try {

        const response =
            await fetch(
                "/api/user/balance",
                {
                    method: "GET",
                    credentials: "same-origin",
                    cache: "no-store",
                    headers: {
                        "Accept": "application/json"
                    }
                }
            );


        if (!response.ok) {
            return;
        }


        const data =
            await response.json();


        if (
            data.balance !== undefined
        ) {

            const balance =
                Number(data.balance);


            const formatted =
                Number.isFinite(balance)
                    ? balance.toLocaleString(
                        "en-IN",
                        {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2
                        }
                    )
                    : "0.00";


            const balanceElement =
                document.getElementById(
                    "balance"
                );


            const betslipBalance =
                document.getElementById(
                    "betslipBalance"
                );


            if (balanceElement) {

                balanceElement.textContent =
                    `₹${formatted}`;

            }


            if (betslipBalance) {

                betslipBalance.textContent =
                    `₹${formatted}`;

            }

        }

    } catch (error) {

        console.warn(
            "Balance loading failed:",
            error
        );

    }

}


/* =========================================================
   BETSLIP
========================================================= */

function setupBetslip() {

    const betslip =
        document.getElementById(
            "betslip"
        );


    const closeButton =
        document.getElementById(
            "betslipClose"
        );


    const mobileButton =
        document.getElementById(
            "mobileBetslipButton"
        );


    if (
        closeButton &&
        betslip
    ) {

        closeButton.addEventListener(
            "click",
            () => {

                betslip.classList.remove(
                    "open"
                );

            }
        );

    }


    if (
        mobileButton &&
        betslip
    ) {

        mobileButton.addEventListener(
            "click",
            () => {

                betslip.classList.toggle(
                    "open"
                );

            }
        );

    }

}


/* =========================================================
   INITIALIZE
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    () => {


        /* FILTERS */

        document
            .querySelectorAll(
                ".sport-filter"
            )
            .forEach(button => {

                button.addEventListener(
                    "click",
                    () => {

                        setFilter(
                            button.dataset.filter
                        );

                    }
                );

            });


        /* DEPOSIT */

        const depositButton =
            document.getElementById(
                "depositBtn"
            );


        if (depositButton) {

            depositButton.addEventListener(
                "click",
                openDepositWhatsApp
            );

        }


        /* WITHDRAW */

        const withdrawButton =
            document.getElementById(
                "withdrawBtn"
            );


        if (withdrawButton) {

            withdrawButton.addEventListener(
                "click",
                openWithdrawWhatsApp
            );

        }


        /* BETSLIP */

        setupBetslip();


        /* BALANCE */

        loadBalance();


        /* MATCHES */

        loadMatches();


        /* MATCH REFRESH */

        setInterval(
            loadMatches,
            10000
        );


        /* BALANCE REFRESH */

        setInterval(
            loadBalance,
            15000
        );

    }
);