* Teaching example for the inspected OneClick 6.0 interface.
* Requires Stata 14+ and an installed oneclick command.
* This file has not been executed in Stata by the skill builder.
* Run in a fresh empty Stata session. It refuses a nonempty data-in-memory state.
version 14

if c(N) > 0 | c(k) > 0 {
    display as error "Run this teaching demo in a fresh empty Stata session."
    exit 4
}

capture which oneclick
if _rc {
    display as error "oneclick is not installed. Inspect/authorize ssc install oneclick first."
    exit 199
}

* All writes go to a fresh Stata tempfile, avoiding a fixed-name result overwrite.
tempfile demo_result
sysuse auto, clear
keep if !missing(price, weight, mpg, rep78)

capture noisily oneclick price mpg rep78, method(regress) pvalue(.05) ///
    fixvar(weight) options(vce(robust)) threshold(1) full ///
    saveplace("`demo_result'")
local oneclick_rc = _rc

if `oneclick_rc' == 0 {
    capture confirm file "`demo_result'"
    if _rc == 0 {
        use "`demo_result'", clear
        describe
        list command direction coef p r2, noobs
        display as text "p is a star string. This is a screened-results file, not all specifications."
    }
    else {
        display as error "Command returned zero but no result file was found; inspect version and paths."
    }
}
else {
    display as text "Return code: `oneclick_rc'. Check the log; no matching subset is one possible outcome."
}
clear
