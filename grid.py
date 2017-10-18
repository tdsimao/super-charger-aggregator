import numpy as np


class Grid(object):
    def __init__(self, n_nodes, n_lines, lines, reactances, line_bounds):
        self.n_nodes = n_nodes
        self.n_lines = n_lines
        self.lines = lines
        self.line_bounds = self._get_line_bounds(line_bounds)
        self.x = self._get_x(reactances)
        self.S = self._compute_ptdfs()

    def _get_x(self, reactances):
        return self._list_to_matrix(reactances)

    def _get_line_bounds(self, line_bounds):
        return self._list_to_matrix(line_bounds)

    def _list_to_matrix(self, alist):
        matrix = np.zeros([self.n_nodes, self.n_nodes])
        for (i, j), bound in zip(self.lines, alist):
            matrix[i][j] = bound
            matrix[j][i] = bound
        return matrix

    @staticmethod
    def load_grid_from_file(file_name):
        with open(file_name, "r") as f:
            first_line = f.readline().split("=")
            assert first_line[0] == "numBus"
            n_nodes = int(first_line[1])

            second_line = f.readline().split("=")
            assert second_line[0] == "numLines"
            n_lines = second_line[1]

            comment_line = f.readline()
            assert comment_line[0] == "#"

            lines = []
            reactances = []
            line_bounds = []
            for line in f.readlines():
                i, j, _, reactance, line_bound = line.split()
                lines.append((int(i), int(j)))
                reactances.append(float(reactance))
                line_bounds.append(float(line_bound))
        return Grid(n_nodes=n_nodes,
                    n_lines=n_lines,
                    lines=lines,
                    reactances=reactances,
                    line_bounds=line_bounds)

    def _compute_ptdfs(self):
        """
        Precomputing Power Transfer Distribution Factors
        """
        z = self._compute_z()
        s = np.zeros([self.n_nodes, self.n_nodes, self.n_nodes])
        for i in range(self.n_nodes):
            for l in range(self.n_nodes):
                for k in range(self.n_nodes):
                    if k == 0 and l != 0:
                        s[k, l, i] = -1 * z[l-1, i-1]
                    elif k != 0 and l == 0:
                        s[k, l, i] = z[k-1, i-1]
                    elif k != 0 and l != 0 and k != l:
                        s[k, l, i] = z[k-1, i-1] - z[l-1, i-1]
        return s

    def _compute_z(self):
        m = self._compute_m()
        return np.linalg.inv(m[1::, 1::])

    def _compute_m(self):
        m = np.zeros([self.n_nodes, self.n_nodes])
        for i in range(self.n_nodes):
            for j in range(self.n_nodes):
                if i != j:
                    m[i, j] = -1./self.x[i, j]
                else:
                    m[i, j] = sum(1./self.x[k, j] for k in range(self.n_nodes) if k != j)
        return m

    def compute_flow(self, loads):
        """
        use precomputed ptdfs to calculate the flow in the grid
        :param loads: vector of load in each node
        :return: flow of the grid given the loads in each node
        """
        assert len(loads) == self.n_nodes
        flow = np.zeros([self.n_nodes, self.n_nodes])
        for k, l in self.lines:
            flow[k, l] = self.line_flow(k, l, loads)
        return flow

    def line_flow(self, k, l, loads):
        return sum(loads[i] * 1. / self.x[k, l] * self.S[k, l, i] for i in range(self.n_nodes - 1))

    def feasible(self, loads):
        flow = self.compute_flow(loads)
        for i, j in self.lines:
            if abs(flow[i, j]) > self.line_bounds[i, j]:
                return False
        return True


def test_grid_feasibility(testing_grid, loads, expected_result):
    assert testing_grid.feasible(loads) == expected_result


if __name__ == "__main__":
    """
    running some tests with the example from [Walraven and Morales-España, 2015]
    """
    grid = Grid.load_grid_from_file('grids/grid_1.txt')

    print(grid.compute_flow([2, 1, -3]))

    test_grid_feasibility(testing_grid=grid, loads=[2, -1, 3], expected_result=True)
    test_grid_feasibility(testing_grid=grid, loads=[-400, 200, 200], expected_result=True)
    test_grid_feasibility(testing_grid=grid, loads=[401, -201, -200], expected_result=False)
    test_grid_feasibility(testing_grid=grid, loads=[401, -200, -201], expected_result=False)
    test_grid_feasibility(testing_grid=grid, loads=[-200, 401, -201], expected_result=False)