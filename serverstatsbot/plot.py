from collections import defaultdict

from .utils import ensure_imports


def plot_all(data, x_axis, y_axis, label, entries, **kwargs):
    import matplotlib.figure

    title = kwargs.get('title', '')
    n = kwargs.get('n', None)
    top = kwargs.get('top', True)
    x_date = kwargs.get('x_date', False)
    y_date = kwargs.get('y_date', False)

    graph = matplotlib.figure.Figure()
    axes = graph.add_subplot()
    axes.set_title(title)

    all_lines = defaultdict(list)
    x_labels = list()
    for i, x_slice in enumerate(data):
        current_slice = x_slice[entries].copy()
        if n:
            current_slice.sort(key=lambda x: x[y_axis], reverse=top)
            if len(current_slice) > n:
                current_slice = current_slice[:n]
        for entry in current_slice:
            line = all_lines[entry[label]]
            line.extend((None, )*(i-len(line)))
            line.append(entry[y_axis])
        x_labels.append(x_slice[x_axis])

    line_len = len(data)
    for line in all_lines.values():
        line.extend((None, )*(line_len-len(line)))

    for name, line in all_lines.items():
        if x_date or y_date:
            axes.plot_date(x_labels, line, xdate=x_date, ydate=y_date, label=name, ls='-')
        else:
            axes.plot(x_labels, line, label = name)

    axes.set_ylabel(y_axis)
    axes.set_xlabel(x_axis)
    axes.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    graph.autofmt_xdate()

    fname = f"output/{title.replace(' ', '_')}.png"
    graph.savefig(fname, bbox_inches="tight")
    return fname