"use strict";

document.addEventListener("DOMContentLoaded", function () {

    /*
     * CrickBet WhatsApp number
     *
     * 91 = India
     * 8895898319 = WhatsApp number
     */
    const whatsappNumber = "918895898319";


    /*
     * Create WhatsApp link
     */
    function createWhatsAppUrl(message) {

        return (
            "https://wa.me/" +
            whatsappNumber +
            "?text=" +
            encodeURIComponent(message)
        );

    }


    /*
     * DEPOSIT
     */
    const depositButton =
        document.getElementById("openDeposit");


    if (depositButton) {

        depositButton.addEventListener(
            "click",
            function () {

                const message =
                    "Hello CrickBet, I want to make a deposit.";


                window.open(
                    createWhatsAppUrl(message),
                    "_blank"
                );

            }
        );

    }


    /*
     * WITHDRAW
     */
    const withdrawButton =
        document.getElementById("openWithdraw");


    if (withdrawButton) {

        withdrawButton.addEventListener(
            "click",
            function () {

                const message =
                    "Hello CrickBet, I want to make a withdrawal.";


                window.open(
                    createWhatsAppUrl(message),
                    "_blank"
                );

            }
        );

    }

});