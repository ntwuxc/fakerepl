# fakerepl
A Jupyter kernel for C++, an interactive environment for a batch compiler

The easiest way to start using it is with Docker.

Build:

````
docker build -t fakerepl
```

Run in the terminal.

```
docker run -it --rm -t fakerepl
```

Run the notebook.

```
docker run -it --rm -p 8888:8888 -v my/notebook/dir:/Notebooks -t fakerepl start-notebook.sh
```


Example use:

```
In [1]: #include <array>

In [2]: #include <algorithm>

In [3]: std::array<int,5> ar{5,3,4,2,1};

In [4]: %action std::sort(ar.begin(), ar.end());

In [5]: ? ar
[1, 2, 3, 4, 5]
```
