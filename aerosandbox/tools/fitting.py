import numpy as np
import casadi as cas


def fit(
        model,  # type: callable
        x_data,  # type: dict
        y_data,  # type: np.ndarray
        param_guesses,  # type: dict
        param_bounds=None,  # type: dict
        weights=None,  # type: np.ndarray
        verbose=True,  # type: bool
):
    """
    Fits a model to data through least-squares minimization.
    :param model: A callable with syntax f(x, p) where:
            x is a dict of dependent variables. Same format as x_data [dict of 1D ndarrays of length n].
            p is a dict of parameters. Same format as param_guesses [dict of scalars].
        Model should use CasADi functions for differentiability.
    :param x_data: a dict of dependent variables. Same format as model's x. [dict of 1D ndarrays of length n]
    :param y_data: independent variable. [1D ndarray of length n]
    :param param_guesses: a dict of fit parameters. Same format as model's p. Keys are parameter names, values are initial guesses. [dict of scalars]
    :param param_bounds: Optional: a dict of bounds on fit parameters.
        Keys are parameter names, values are a tuple of (min, max).
        May contain only a subset of param_guesses if desired.
        Use None to represent one-sided constraints (i.e. (None, 5)).
        [dict of tuples]
    :param weights: Optional: weights for data points. If not supplied, weights are assumed to be uniform.
        Weights are automatically normalized. [1D ndarray of length n]
    :param verbose: Whether or not to print information about parameters and goodness of fit.
    :return: Optimal fit parameters [dict]
    """
    opti = cas.Opti()

    # Handle weighting
    if weights is None:
        weights = cas.GenDM_ones(y_data.shape[0])
    weights /= cas.sum1(weights)

    def fit_param(initial_guess, lower_bound=None, upper_bound=None):
        """
        Helper function to create a fit variable
        :param initial_guess:
        :param lower_bound:
        :param upper_bound:
        :return:
        """
        var = opti.variable()
        opti.set_initial(var, initial_guess)
        if lower_bound is not None:
            opti.subject_to(var > lower_bound)
        if upper_bound is not None:
            opti.subject_to(var < upper_bound)
        return var

    if param_bounds is None:
        params = {
            k: fit_param(param_guesses[k])
            for k in param_guesses
        }
    else:
        params = {
            k: fit_param(param_guesses[k]) if k not in param_bounds else
            fit_param(param_guesses[k], param_bounds[k][0], param_bounds[k][1])
            for k in param_guesses
        }

    y_model = model(x_data, params)

    residuals = y_model - y_data
    opti.minimize(cas.sum1(weights * residuals ** 2))

    opti.solver('ipopt')
    sol = opti.solve()

    params_solved = {}
    for k in params:
        try:
            params_solved[k] = sol.value(params[k])
        except:
            params_solved[k] = np.NaN

    # printing
    if verbose:
        # Print parameters
        print("\nFit Parameters:")
        if len(params_solved) <= 20:
            [print("\t%s: %f" % (k, v)) for k, v in params_solved.items()]
        else:
            print("\t%i parameters solved for." % len(params_solved))
        print("\nGoodness of Fit:")

        # Print RMS error
        weighted_RMS_error = sol.value(cas.sqrt(cas.sum1(
            weights * residuals ** 2
        )))
        print("\tWeighted RMS error: %f" % weighted_RMS_error)

        # Print R^2
        y_data_mean = cas.sum1(y_data) / y_data.shape[0]
        SS_tot = cas.sum1(weights * (y_data - y_data_mean) ** 2)
        SS_res = cas.sum1(weights * (y_data - y_model) ** 2)
        R_squared = sol.value(1 - SS_res / SS_tot)
        print("\tR^2: %f" % R_squared)

    return params_solved