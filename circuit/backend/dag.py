class DAG:
    """Directed Acyclic Graph utility"""
    def __init__(self):
        self.adjacencies: dict[str: list] = {}
        self.marked = {}

    def add_node(self, name, allow_exist=False):
        if name in self.adjacencies.keys():
            if allow_exist:
                return
            raise KeyError("Node already exists!")
        self.adjacencies[name] = []

    def connect(self, from_, to):
        assert from_ in self.adjacencies.keys() and to in self.adjacencies.keys()
        if self.connection_exists(from_, to):
            return
        if self.connection_exists(to, from_):
            raise ValueError("Cannot connect due to acyclic graph condition")
        self.adjacencies[from_].append(to)

    def get_children(self, name):
        return self.adjacencies[name]

    def init_marked(self):
        self.marked = {}
        for k in self.adjacencies:
            self.marked[k] = False

    def connection_exists(self, from_, to):
        self.init_marked()
        self.dfs(from_)
        return self.marked[to]

    def dfs(self, from_):
        self.marked[from_] = True
        for child in self.get_children(from_):
            if not self.marked[child]:
                self.dfs(child)

    def get_bottom_layer(self):
        bottom_layer = []
        for k in self.adjacencies:
            if len(self.adjacencies[k]) == 0:
                bottom_layer.append(k)
        return bottom_layer

    def get_top_layer(self):
        top_layer = set(self.adjacencies.keys())
        for k in self.adjacencies:
            for child in self.adjacencies[k]:
                if child in top_layer:
                    top_layer.remove(child)
        return list(top_layer)

if __name__ == "__main__":
    dag = DAG()
    dag.add_node("a")
    dag.add_node("b")
    dag.add_node("c")
    dag.add_node("d")
    dag.add_node("e")
    dag.add_node("f")
    dag.add_node("g")

    dag.connect("a", "b")
    dag.connect("a", "c")
    dag.connect("b", "d")
    dag.connect("b", "e")
    dag.connect("c", "e")
    dag.connect("f", "c")
    dag.connect("f", "g")
    dag.connect("g", "a")

    print(dag.get_bottom_layer())
    print(dag.get_top_layer())
