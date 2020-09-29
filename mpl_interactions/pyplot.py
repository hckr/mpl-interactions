from collections.abc import Callable, Iterable
from functools import partial
from numbers import Number

import numpy as np
from matplotlib.cbook.deprecation import deprecated
from matplotlib.collections import PatchCollection
from matplotlib.colors import to_rgba_array
from matplotlib.patches import Rectangle
from matplotlib.pyplot import sca, sci

from .controller import Controls, gogogo_controls

from .helpers import (
    broadcast_many,
    callable_else_value,
    callable_else_value_wrapper,
    eval_xy,
    create_slider_format_dict,
    gogogo_display,
    gogogo_figure,
    kwarg_to_ipywidget,
    kwarg_to_mpl_widget,
    notebook_backend,
    update_datalim_from_bbox,
)

# functions that are methods
__all__ = [
    "interactive_plot_factory",
    "interactive_plot",
    "interactive_hist",
    "interactive_scatter",
    "interactive_imshow",
]


def interactive_plot(
    *args,
    xlim="stretch",
    ylim="stretch",
    slider_formats=None,
    title=None,
    ax=None,
    force_ipywidgets=False,
    play_buttons=False,
    play_button_pos="right",
    controls=None,
    display_controls=True,
    **kwargs,
):
    """
    Control a plot using widgets

    interactive_plot([x], y, [fmt])

    where x/y is are either arraylike or a function that returns arrays. Any kwargs accepted by
    matplotlib.pyplot.plot will be passed through, other kwargs will be intrepreted as controls

    parameters
    ----------
    x, y : array-like or scalar or function
        The horizontal / vertical coordinates of the data points.
        *x* values are optional and default to ``range(len(y))``. If both *x* and *y* are
        provided and *y* is a function then it will be called as ``y(x, **params)``. If
        *x* is a function it will be called as ``x(**params)``
    fmt : str, optional
        A format string, e.g. 'ro' for red circles. See matplotlib.pyplot.plot
        for full documentation.
    xlim : string or tuple of floats, optional
        If a tuple it will be passed to ax.set_xlim. Other options are:
        'auto': rescale the x axis for every redraw
        'stretch': only ever expand the xlims.
    ylim : string or tuple of floats, optional
        If a tuple it will be passed to ax.set_ylim. Other options are same
        as xlim
    slider_formats : None, string, or dict
        If None a default value of decimal points will be used. Uses the new {} style formatting
    title : None or string
        If a string then you can have it update automatically using string formatting of the names
        of the parameters. i.e. to include the current value of tau: title='the value of tau is: {tau:.2f}'
    ax : matplotlib axis, optional
        The axis on which to plot. If none the current axis will be used.
    force_ipywidgets : boolean
        If True ipywidgets will always be used, even if not using the ipympl backend.
        If False the function will try to detect if it is ok to use ipywidgets
        If ipywidgets are not used the function will fall back on matplotlib widgets
    play_buttons : bool or dict, optional
        Whether to attach an ipywidgets.Play widget to any sliders that get created.
        If a boolean it will apply to all kwargs, if a dictionary you choose which sliders you
        want to attach play buttons too.
    play_button_pos : str, or dict, or list(str)
        'left' or 'right'. Whether to position the play widget(s) to the left or right of the slider(s)
    controls : mpl_interactions.controller.Controls
        An existing controls object if you want to tie multiple plot elements to the same set of
        controls
    display_controls : boolean
        Whether the controls should display themselve on creation. Ignored if controls is specified.

    returns
    -------
    controls

    Examples
    --------

    With numpy arrays::

        x = np.linspace(0,2*np.pi)
        tau = np.linspace(0, np.pi)
        def f(tau):
            return np.sin(x*tau)
        interactive_plot(f, tau=tau)

    with tuples::

        x = np.linspace(0,2*np.pi)
        def f(x, tau):
            return np.sin(x+tau)
        interactive_plot(x, f, tau=(0, np.pi, 1000))

    """
    # this is a list of options to Line2D partially taken from
    # https://github.com/matplotlib/matplotlib/blob/f9d29189507cfe4121a231f6ab63539d216c37bd/lib/matplotlib/lines.py#L271
    # many of these can also be made into functions
    plot_kwargs_list = [
        "linewidth",
        "linestyle",
        "color",
        "marker",
        "markersize",
        "markeredgewidth",
        "markeredgecolor",
        "markerfacecolor",
        "markerfacecoloralt",
        "fillstyle",
        "antialiased",
        "dash_capstyle",
        "solid_capstyle",
        "dash_joinstyle",
        "solid_joinstyle",
        "pickradius",
        "drawstyle",
        "markevery",
        "label",
    ]
    plot_kwargs = {}
    for k in plot_kwargs_list:
        if k in kwargs:
            plot_kwargs[k] = kwargs.pop(k)
    x_and_y = False
    x = None
    fmt = None
    if len(args) == 0:
        # wot...
        return
    elif len(args) == 1:
        y = args[0]
    elif len(args) == 2:
        # either (y, fmt) or (x, y)
        # hard to know for sure though bc fmt can be a function
        # or maybe just requirement that fmt is a function
        if isinstance(args[1], str):
            y, fmt = args
        else:
            x_and_y = True
            x, y = args
    elif len(args) == 3:
        x_and_y = True
        x, y, fmt = args
    else:
        raise ValueError(f"You passed in {len(args)} args, but no more than 3 is supported.")

    ipympl = notebook_backend()
    use_ipywidgets = ipympl or force_ipywidgets
    fig, ax = gogogo_figure(ipympl, ax=ax)
    slider_formats = create_slider_format_dict(slider_formats, use_ipywidgets)
    controls, params = gogogo_controls(
        kwargs, controls, display_controls, slider_formats, play_buttons, play_button_pos
    )

    def update(params, indices):
        if x_and_y:
            x_, y_ = eval_xy(x, y, params)
            line.set_data(x_, y_)
        else:
            line.set_ydata(callable_else_value(y, params))

        cur_xlims = ax.get_xlim()
        cur_ylims = ax.get_ylim()
        ax.relim()  # this may be expensive? don't do if not necessary?
        if ylim == "auto":
            ax.autoscale_view(scalex=False)
        elif ylim == "stretch":
            new_lims = [ax.dataLim.y0, ax.dataLim.y0 + ax.dataLim.height]
            new_lims = [
                new_lims[0] if new_lims[0] < cur_ylims[0] else cur_ylims[0],
                new_lims[1] if new_lims[1] > cur_ylims[1] else cur_ylims[1],
            ]
            ax.set_ylim(new_lims)
        if xlim == "auto":
            ax.autoscale_view(scaley=False)
        elif xlim == "stretch":
            new_lims = [ax.dataLim.x0, ax.dataLim.x0 + ax.dataLim.width]
            new_lims = [
                new_lims[0] if new_lims[0] < cur_xlims[0] else cur_xlims[0],
                new_lims[1] if new_lims[1] > cur_xlims[1] else cur_xlims[1],
            ]
            ax.set_xlim(new_lims)
        if title is not None:
            ax.set_title(title.format(**params))

    controls.register_function(update, fig, params.keys())

    if x_and_y:
        x_, y_ = eval_xy(x, y, params)
        if fmt:
            line = ax.plot(x_, y_, fmt, **plot_kwargs)[0]
        else:
            line = ax.plot(x_, y_, **plot_kwargs)[0]
    else:
        y_ = callable_else_value(y, params)
        if fmt:
            line = ax.plot(y_, fmt, **plot_kwargs)[0]
        else:
            line = ax.plot(y_, **plot_kwargs)[0]

    if not isinstance(xlim, str):
        ax.set_xlim(xlim)
    if not isinstance(ylim, str):
        ax.set_ylim(ylim)
    if title is not None:
        ax.set_title(title.format(**params))

    # make sure the home button will work
    if hasattr(fig.canvas, "toolbar") and fig.canvas.toolbar is not None:
        fig.canvas.toolbar.push_current()

    return controls


@deprecated(
    "0.6.1", alternative="interactive_plot with the ax argument", name="heck", removal="0.7.0"
)
def interactive_plot_factory(
    ax,
    f,
    x=None,
    xlim="stretch",
    ylim="stretch",
    slider_format_string=None,
    plot_kwargs=None,
    title=None,
    use_ipywidgets=None,
    play_buttons=False,
    play_button_pos="right",
    **kwargs,
):
    """
    Use this function for maximum control over layout of the widgets.

    parameters
    ----------
    ax : matplotlib axes
    f : function or iterable of functions
    use_ipywidgets : None or boolean, optional
        If None will attempt to infer whether to use ipywidgets based on the backend. Use
        True or False to ensure ipywidgets is or is not used.
    play_buttons : bool or dict, optional
        Whether to attach an ipywidgets.Play widget to any sliders that get created.
        If a boolean it will apply to all kwargs, if a dictionary you choose which sliders you
        want to attach play buttons too.
    play_button_pos : str, or dict, or list(str)
        'left' or 'right'. Whether to position the play widget(s) to the left or right of the slider(s)
    """
    return interactive_plot(
        f,
        x=x,
        xlim=xlim,
        ylim=ylim,
        slider_format_string=slider_format_string,
        plot_kwargs=plot_kwargs,
        title=title,
        ax=ax,
        display=False,
        force_ipywidgets=use_ipywidgets,
        play_buttons=play_buttons,
        play_button_pos=play_button_pos,
        **kwargs,
    )[-1].children


def simple_hist(arr, bins="auto", density=None, weights=None):
    heights, bins = np.histogram(arr, bins=bins, density=density, weights=weights)
    width = bins[1] - bins[0]
    new_patches = []
    for i in range(len(heights)):
        new_patches.append(Rectangle((bins[i], 0), width=width, height=heights[i]))
    xlims = (bins.min(), bins.max())
    ylims = (0, heights.max() * 1.05)

    return xlims, ylims, new_patches


def stretch(ax, xlims, ylims):
    cur_xlims = ax.get_xlim()
    cur_ylims = ax.get_ylim()
    new_lims = ylims
    new_lims = [
        new_lims[0] if new_lims[0] < cur_ylims[0] else cur_ylims[0],
        new_lims[1] if new_lims[1] > cur_ylims[1] else cur_ylims[1],
    ]
    ax.set_ylim(new_lims)
    new_lims = xlims
    new_lims = [
        new_lims[0] if new_lims[0] < cur_xlims[0] else cur_xlims[0],
        new_lims[1] if new_lims[1] > cur_xlims[1] else cur_xlims[1],
    ]
    ax.set_xlim(new_lims)


def interactive_hist(
    f,
    density=False,
    bins="auto",
    weights=None,
    ax=None,
    slider_formats=None,
    display=True,
    force_ipywidgets=False,
    play_buttons=False,
    play_button_pos="right",
    controls=None,
    display_controls=True,
    **kwargs,
):
    """
    Control the contents of a histogram using widgets.

    See https://github.com/ianhi/mpl-interactions/pull/73#issue-470638134 for a discussion
    of the limitations of this function. These limitations will be improved once
    https://github.com/matplotlib/matplotlib/pull/18275 has been merged.

    parameters
    ----------
    f : function
        A function that will return a 1d array of which to take the histogram
    density : bool, optional
        whether to plot as a probability density. Passed to np.histogram
    bins : int or sequence of scalars or str, optional
        bins argument to np.histogram
    weights : array_like, optional
        passed to np.histogram
    ax : matplotlib axis, optional
        If None a new figure and axis will be created
    slider_format_string : None, string, or dict
        If None a default value of decimal points will be used. For ipywidgets this uses the new f-string formatting
        For matplotlib widgets you need to use `%` style formatting. A string will be used as the default
        format for all values. A dictionary will allow assigning different formats to different sliders.
        note: For matplotlib >= 3.3 a value of None for slider_format_string will use the matplotlib ScalarFormatter
        object for matplotlib slider values.
    display : boolean
        If True then the output and controls will be automatically displayed
    force_ipywidgets : boolean
        If True ipywidgets will always be used, even if not using the ipympl backend.
        If False the function will try to detect if it is ok to use ipywidgets
        If ipywidgets are not used the function will fall back on matplotlib widgets
    play_buttons : bool or dict, optional
        Whether to attach an ipywidgets.Play widget to any sliders that get created.
        If a boolean it will apply to all kwargs, if a dictionary you choose which sliders you
        want to attach play buttons too.
    play_button_pos : str, or dict, or list(str)
        'left' or 'right'. Whether to position the play widget(s) to the left or right of the slider(s)
    controls : mpl_interactions.controller.Controls
        An existing controls object if you want to tie multiple plot elements to the same set of
        controls
    display_controls : boolean
        Whether the controls should display themselve on creation. Ignored if controls is specified.

    returns
    -------
    controls

    Examples
    --------

    With numpy arrays::

        loc = np.linspace(-5, 5, 500)
        scale = np.linspace(1, 10, 100)
        def f(loc, scale):
            return np.random.randn(1000)*scale + loc
        interactive_hist(f, loc=loc, scale=scale)

    with tuples::

        def f(loc, scale):
            return np.random.randn(1000)*scale + loc
        interactive_hist(f, loc=(-5, 5, 500), scale=(1, 10, 100))
    """

    funcs = np.atleast_1d(f)
    # supporting more would require more thought
    if len(funcs) != 1:
        raise ValueError(
            f"Currently only a single function is supported. You passed in {len(funcs)} functions"
        )

    ipympl = notebook_backend()
    fig, ax = gogogo_figure(ipympl, ax=ax)
    use_ipywidgets = ipympl or force_ipywidgets
    slider_formats = create_slider_format_dict(slider_formats, use_ipywidgets)
    controls, params = gogogo_controls(
        kwargs, controls, display_controls, slider_formats, play_buttons, play_button_pos
    )
    pc = PatchCollection([])
    ax.add_collection(pc, autolim=True)

    # update plot
    def update(params, indices):
        arr = funcs[0](**params)
        new_x, new_y, new_patches = simple_hist(arr, density=density, bins=bins, weights=weights)
        stretch(ax, new_x, new_y)
        pc.set_paths(new_patches)
        ax.autoscale_view()

    controls.register_function(update, fig, params.keys())

    new_x, new_y, new_patches = simple_hist(
        funcs[0](**params), density=density, bins=bins, weights=weights
    )
    pc.set_paths(new_patches)
    ax.set_xlim(new_x)
    ax.set_ylim(new_y)

    return controls


def interactive_scatter(
    x,
    y,
    s=None,
    c=None,
    cmap=None,
    vmin=None,
    vmax=None,
    alpha=None,
    edgecolors=None,
    label=None,
    xlim="stretch",
    ylim="stretch",
    ax=None,
    slider_formats=None,
    title=None,
    display=True,
    force_ipywidgets=False,
    play_buttons=False,
    play_button_pos="right",
    controls=None,
    display_controls=True,
    **kwargs,
):
    """
    Control a scatter plot using widgets.

    parameters
    ----------
    x : function or array-like
        Must be broadcastable with y and any plotting kwargs. Can be a mix
        of numbers and functions. Any functions in x must return a 1D array
        or list of the same length as the paired y function or array
    y : function or array-like
        see x
    c : array-like or list of colors or color, broadcastable
        Must be broadcastable to x,y and any other plotting kwargs.
        valid input to plt.scatter, or an array of valid inputs, or a function
        or an array-like of functions of the same length as f
    s : float or array-like or function, broadcastable
        valid input to plt.scatter, or an array of valid inputs, or a function
        or an array-like of functions of the same length as f
    alpha : float, None, or function(s), broadcastable
        Affects all scatter points. This will compound with any alpha introduced by
        the ``c`` argument
    edgecolors : colorlike, broadcastable
        passed through to scatter.
    label : string(s) broadcastable
        labels for the functions being plotted.
    xlim : string or tuple of floats, optional
        If a tuple it will be passed to ax.set_xlim. Other options are:
        'auto': rescale the x axis for every redraw
        'stretch': only ever expand the xlims.
    ylim : string or tuple of floats, optional
        If a tuple it will be passed to ax.set_ylim. Other options are same
        as xlim
    ax : matplotlib axis, optional
        If None a new figure and axis will be created
    slider_formats : None, string, or dict
        If None a default value of decimal points will be used. For ipywidgets this uses the new f-string formatting
        For matplotlib widgets you need to use `%` style formatting. A string will be used as the default
        format for all values. A dictionary will allow assigning different formats to different sliders.
        note: For matplotlib >= 3.3 a value of None for slider_formats will use the matplotlib ScalarFormatter
        object for matplotlib slider values.
    title : None or string
        If a string then you can have it update automatically using string formatting of the names
        of the parameters. i.e. to include the current value of tau: title='the value of tau is: {tau:.2f}'
    display : boolean
        If True then the output and controls will be automatically displayed
    force_ipywidgets : boolean
        If True ipywidgets will always be used, even if not using the ipympl backend.
        If False the function will try to detect if it is ok to use ipywidgets
        If ipywidgets are not used the function will fall back on matplotlib widgets
    play_buttons : bool or dict or list(str), optional
        Whether to attach an ipywidgets.Play widget to any sliders that get created.
        If a boolean it will apply to all kwargs, if a dictionary you choose which sliders you
        want to attach play buttons too. If a list of strings use the names of the parameters that
        you want to have sliders
    play_button_pos : str, or dict, or list(str)
        'left' or 'right'. Whether to position the play widget(s) to the left or right of the slider(s)
    controls : mpl_interactions.controller.Controls
        An existing controls object if you want to tie multiple plot elements to the same set of
        controls
    display_controls : boolean
        Whether the controls should display themselve on creation. Ignored if controls is specified.

    returns
    -------
    controls
    """

    def _prep_color(col):
        if (
            isinstance(col, np.ndarray)
            and np.issubdtype(col.dtype, np.number)
            and col.ndim == 2
            and col.shape[1] in [3, 4]
        ):
            return col[None, :, :]
        else:
            return col

    def _prep_size(s):
        if (isinstance(s, tuple) or isinstance(s, list)) and all(
            [isinstance(es, Number) for es in s]
        ):
            return np.asarray(s, dtype=np.object)
        return s

    X, Y, cols, sizes, edgecolors, alphas, labels = broadcast_many(
        (x, "x"),
        (y, "y"),
        (_prep_color(c), "c"),
        (_prep_size(s), "s"),
        (_prep_color(edgecolors), "edgecolors"),
        (alpha, "alpha"),
        (label, "labels"),
    )

    if isinstance(xlim, str):
        stretch_x = xlim == "stretch"
    else:
        stretch_x = False

    if isinstance(ylim, str) and ylim.lower() == "stretch":
        stretch_y = True
    else:
        stretch_y = False

    ipympl = notebook_backend()
    fig, ax = gogogo_figure(ipympl, ax)
    use_ipywidgets = ipympl or force_ipywidgets
    slider_formats = create_slider_format_dict(slider_formats, use_ipywidgets)
    controls, params = gogogo_controls(
        kwargs, controls, display_controls, slider_formats, play_buttons, play_button_pos
    )
    scats = []
    cache = {}

    def update(params, indices):
        if title is not None:
            ax.set_title(title.format(**params))
        for scat, x_, y_, c_, s_, ec_, alpha_ in zip(scats, X, Y, cols, sizes, edgecolors, alphas):
            x, y = eval_xy(x_, y_, params, cache)
            scat.set_offsets(np.column_stack([x, y]))
            c = check_callable_xy(c_, x, y, params)
            s = check_callable_xy(s_, x, y, params)
            ec = check_callable_xy(ec_, x, y, params)
            a = check_callable_alpha(alpha_, params)
            if c is not None:
                try:
                    c = to_rgba_array(c)
                except ValueError as array_err:
                    try:
                        c = scat.cmap(c)
                    except TypeError as cmap_err:
                        raise ValueError(
                            "If c is a function it must return either an RGB(A) array"
                            "or a 1D array of valid color names or values to be colormapped"
                        )
                scat.set_facecolor(c)
            if ec is not None:
                scat.set_edgecolor(ec)
            if s is not None and not isinstance(s, Number):
                scat.set_sizes(s)
            if a is not None:
                scat.set_alpha(a)

            update_datalim_from_bbox(
                ax, scat.get_datalim(ax.transData), stretch_x=stretch_x, stretch_y=stretch_y
            )
        cache.clear()
        ax.autoscale_view()

    controls.register_function(update, fig, params.keys())
    if title is not None:
        ax.set_title(title.format(**params))

    def check_callable_xy(arg, x, y, params):
        if isinstance(arg, Callable):
            if arg not in cache:
                cache[arg] = arg(x, y, **params)
            return cache[arg]
        else:
            return arg

    def check_callable_alpha(alpha_, params):
        if isinstance(alpha_, Callable):
            if not alpha_ in cache:
                cache[alpha_] = alpha_(**params)
            return cache[alpha_]
        else:
            return alpha_

    for x_, y_, c_, s_, ec_, alpha_, label_ in zip(X, Y, cols, sizes, edgecolors, alphas, labels):
        x, y = eval_xy(x_, y_, params)
        c = check_callable_xy(c_, x, y, params)
        s = check_callable_xy(s_, x, y, params)
        ec = check_callable_xy(ec_, x, y, params)
        a = check_callable_alpha(alpha_, params)
        scats.append(
            ax.scatter(
                x,
                y,
                c=c,
                s=s,
                vmin=vmin,
                vmax=vmax,
                cmap=cmap,
                alpha=a,
                edgecolors=ec,
                label=label_,
            )
        )
        if title is not None:
            ax.set_title(title.format(**params))

    cache.clear()
    return controls


# portions of this docstring were copied directly from the docsting
# of `matplotlib.pyplot.imshow`
def interactive_imshow(
    X,
    cmap=None,
    norm=None,
    aspect=None,
    interpolation=None,
    alpha=None,
    vmin=None,
    vmax=None,
    origin=None,
    extent=None,
    autoscale_cmap=True,
    filternorm=True,
    filterrad=4.0,
    resample=None,
    url=None,
    ax=None,
    slider_formats=None,
    title=None,
    display=True,
    force_ipywidgets=False,
    play_buttons=False,
    play_button_pos="right",
    controls=None,
    display_controls=True,
    **kwargs,
):
    """
    Control an image using widgets.

    parameters
    ----------
    X : function or image like
        If a function it must return an image-like object. See matplotlib.pyplot.imshow for the
        full set of valid options.
    cmap : str or `~matplotlib.colors.Colormap`
        The Colormap instance or registered colormap name used to map
        scalar data to colors. This parameter is ignored for RGB(A) data.
        forwarded to matplotlib
    norm : `~matplotlib.colors.Normalize`, optional
        The `.Normalize` instance used to scale scalar data to the [0, 1]
        range before mapping to colors using *cmap*. By default, a linear
        scaling mapping the lowest value to 0 and the highest to 1 is used.
        This parameter is ignored for RGB(A) data.
        forwarded to matplotlib
    autoscale_cmap : bool
        If True rescale the colormap for every function update. Will not update
        if vmin and vmax are provided or if the returned image is RGB(A) like.
        forwarded to matplotlib
    aspect : {'equal', 'auto'} or float
        forwarded to matplotlib
    interpolation : str
        forwarded to matplotlib
    ax : matplotlib axis, optional
        if None a new figure and axis will be created
    slider_formats : None, string, or dict
        If None a default value of decimal points will be used. For ipywidgets this uses the new f-string formatting
        For matplotlib widgets you need to use `%` style formatting. A string will be used as the default
        format for all values. A dictionary will allow assigning different formats to different sliders.
        note: For matplotlib >= 3.3 a value of None for slider_formats will use the matplotlib ScalarFormatter
        object for matplotlib slider values.
    title : None or string
        If a string then you can have it update automatically using string formatting of the names
        of the parameters. i.e. to include the current value of tau: title='the value of tau is: {tau:.2f}'
    display : boolean
        If True then the output and controls will be automatically displayed
    force_ipywidgets : boolean
        If True ipywidgets will always be used, even if not using the ipympl backend.
        If False the function will try to detect if it is ok to use ipywidgets
        If ipywidgets are not used the function will fall back on matplotlib widgets
    play_buttons : bool or dict or list(str), optional
        Whether to attach an ipywidgets.Play widget to any sliders that get created.
        If a boolean it will apply to all kwargs, if a dictionary you choose which sliders you
        want to attach play buttons too. If a list of strings use the names of the parameters that
        you want to have sliders
    play_button_pos : str, or dict, or list(str)
        'left' or 'right'. Whether to position the play widget(s) to the left or right of the slider(s)

    returns
    -------
    fig : matplotlib figure
    ax : matplotlib axis
    controls : list of widgets
    """
    ipympl = notebook_backend()
    fig, ax = gogogo_figure(ipympl, ax)
    use_ipywidgets = ipympl or force_ipywidgets
    slider_formats = create_slider_format_dict(slider_formats, use_ipywidgets)

    controls, params = gogogo_controls(
        kwargs, controls, display_controls, slider_formats, play_buttons, play_button_pos
    )

    def update(params, indices):
        if title is not None:
            ax.set_title(title.format(**params))

        if isinstance(X, Callable):
            new_data = np.asarray(X(**params))
            im.set_data(new_data)
            if autoscale_cmap and (new_data.ndim != 3) and vmin is None and vmax is None:
                im.norm.autoscale(new_data)
        if isinstance(vmin, Callable):
            im.norm.vmin = vmin(**params)
        if isinstance(vmax, Callable):
            im.norm.vmax = vmax(**params)

    controls.register_function(update, fig, params.keys())

    # make it once here so we can use the dims in update
    new_data = callable_else_value(X, {k: controls.params[k] for k in kwargs})
    im = ax.imshow(
        new_data,
        cmap=cmap,
        norm=norm,
        aspect=aspect,
        interpolation=interpolation,
        alpha=alpha,
        vmin=callable_else_value(vmin, params),
        vmax=callable_else_value(vmax, params),
        origin=origin,
        extent=extent,
        filternorm=filternorm,
        filterrad=filterrad,
        resample=resample,
        url=url,
    )
    # this is necessary to make calls to plt.colorbar behave as expected
    sci(im)
    if title is not None:
        ax.set_title(title.format(**params))
    return controls
