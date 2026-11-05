col_btn, _ = st.columns([2, 1])
    with col_btn:
        if st.button("⚡ GENERATE SPORTYBET BOOKING CODE FOR THIS SLIP", use_container_width=True):
            if sportybet:
                with st.spinner("Connecting to SportyBet Server & Booking Ticket..."):
                    res = sportybet.generate_sportybet_code(legs)
                    # Safe unpack: works whether a tuple or string is returned
                    if isinstance(res, tuple):
                        code = res[0]
                        err = res[1] if len(res) > 1 else None
                    else:
                        code = res
                        err = None

                    if code:
                        st.session_state["cashout_sporty_code"] = code
                        st.success(f"SportyBet Slip Booked! Code: {code}")
                    else:
                        st.error(f"SportyBet notice: {err or 'Could not complete booking'}")
            else:
                st.error("sportybet.py module missing.")
