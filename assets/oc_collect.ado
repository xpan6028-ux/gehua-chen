* Original extension, not part of Shutter Zor's OneClick. Loaded in a child session.
capture program drop oc_collect
program define oc_collect
    version 14
    syntax, HANDLE(name) SPEC(integer) TARGET(name) ///
        COMMAND(string) POLICY(string) ALPHA(real) [CONTROLS(string)]
    tempname n b se stat dfr dft pv lo hi rtwo ra rp ll conv used complete pass B O
    foreach s in n b se stat dfr dft pv lo hi rtwo ra rp ll conv used complete pass {
        scalar ``s'' = .
    }
    local est_rc = .
    local inf_rc = .
    local status "estimation_failed"
    ereturn clear
    display as text "SPEC `spec': `command'"
    capture noisily `command'
    local est_rc = _rc
    if `est_rc' == 0 {
        foreach pair in "n N" "dfr df_r" "rtwo r2" "ra r2_a" "rp r2_p" "ll ll" "conv converged" {
            gettoken dest src : pair
            capture scalar ``dest'' = e(`src')
        }
        capture quietly count if e(sample)
        if _rc == 0 {
            scalar `used' = r(N)
            if "`policy'" == "common" scalar `complete' = (`used' == _N)
        }
        local status "target_absent"
        capture matrix `B' = e(b)
        if _rc == 0 {
            local col = colnumb(`B', "`target'")
            if !missing(`col') {
                local status "target_omitted"
                capture _ms_omit_info `B'
                local omit_rc = _rc
                if `omit_rc' == 0 matrix `O' = r(omit)
                if `omit_rc' != 0 {
                    local status "omission_check_failed"
                }
                else if `O'[1,`col'] == 0 {
                    capture scalar `b' = _b[`target']
                    capture scalar `se' = _se[`target']
                    local status "invalid_standard_error"
                    if !missing(`b', `se') & `se' > 0 {
                        local status "not_converged"
                        if missing(`conv') | `conv' != 0 {
                            local status "inference_failed"
                            capture quietly lincom `target', level(95)
                            local inf_rc = _rc
                            if `inf_rc' == 0 {
                                scalar `pv' = r(p)
                                capture scalar `dft' = r(df)
                                scalar `lo' = r(lb)
                                scalar `hi' = r(ub)
                                scalar `stat' = `b' / `se'
                                local status "invalid_inference"
                                if !missing(`pv') & inrange(`pv', 0, 1) {
                                    local status "ok"
                                    scalar `pass' = (`pv' < `alpha')
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    if "`status'" != "ok" {
        scalar `pv' = .
        scalar `lo' = .
        scalar `hi' = .
        scalar `pass' = .
    }
    local k : word count `controls'
    post `handle' (`spec') (`k') ("`controls'") ("`command'") ///
        ("`policy'") (`est_rc') (`inf_rc') ("`status'") ///
        (`n') (`b') (`se') (`stat') (`dfr') (`dft') (`pv') (`lo') (`hi') ///
        (`rtwo') (`ra') (`rp') (`ll') (`conv') (`used') (`complete') (`pass')
end
