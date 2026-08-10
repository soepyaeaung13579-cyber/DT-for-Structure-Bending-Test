function [node_coords, element_connectivity, mesh_info] = generate_mesh_3d(geometry, mesh_params, element_type, hole_params)
% =========================================================================
% generate_mesh_3d: Generates a 3D mesh for various element types.
% =========================================================================

    Lx = geometry.Lx; Ly = geometry.Ly; Lz = geometry.Lz;
    nx = mesh_params.nx; ny = mesh_params.ny; nz = mesh_params.nz;

    switch element_type
        case 'Hexa8'
            [node_coords, element_connectivity, mesh_info] = generate_hexa8_mesh(Lx, Ly, Lz, nx, ny, nz, hole_params);
        case 'Hexa20'
            [node_coords, element_connectivity, mesh_info] = generate_hexa20_mesh(Lx, Ly, Lz, nx, ny, nz, hole_params);
        case 'Tet4'
            [node_coords, element_connectivity, mesh_info] = generate_tet4_mesh(Lx, Ly, Lz, nx, ny, nz, hole_params);
        case 'Tet10'
            [node_coords, element_connectivity, mesh_info] = generate_tet10_mesh(Lx, Ly, Lz, nx, ny, nz, hole_params);
        otherwise
            error('Unsupported element type: %s', element_type);
    end
    mesh_info.element_type = element_type;
end

% -------------------------------------------------------------------------
% Sub-functions for mesh generation
% -------------------------------------------------------------------------

function [node_coords, connectivity] = apply_square_hole(node_coords, connectivity, Lx, Ly, hole_params)
    if isempty(hole_params) || hole_params.size <= 0
        return;
    end

    cx = hole_params.cx;
    cy = hole_params.cy;
    hole_size = hole_params.size;
    half_size = hole_size / 2.0;

    elem_nodes_coords = node_coords(connectivity, :);
    
    is_inside = ...
        (elem_nodes_coords(:, 1:8, 1) >= cx - half_size) & (elem_nodes_coords(:, 1:8, 1) <= cx + half_size) & ...
        (elem_nodes_coords(:, 1:8, 2) >= cy - half_size) & (elem_nodes_coords(:, 1:8, 2) <= cy + half_size);

    remove_element = all(is_inside, 2);
    
    connectivity(remove_element, :) = [];
    
    if isempty(connectivity)
        node_coords = [];
        return;
    end
    
    used_nodes = unique(connectivity(:));
    node_map = -ones(size(node_coords, 1), 1);
    node_map(used_nodes) = 1:length(used_nodes);
    
    node_coords = node_coords(used_nodes, :);
    connectivity = node_map(connectivity);
end

function [node_coords, connectivity, mesh_info] = generate_hexa8_mesh(Lx, Ly, Lz, nx, ny, nz, hole_params)
    x = linspace(0, Lx, nx + 1);
    y = linspace(0, Ly, ny + 1);
    z = linspace(0, Lz, nz + 1);
    [X, Y, Z] = meshgrid(x, y, z);
    node_coords = [X(:), Y(:), Z(:)];

    elems = zeros(nx * ny * nz, 8);
    elem_idx = 1;
    for i = 1:nx
        for j = 1:ny
            for k = 1:nz
                n1 = (i-1)*(ny+1)*(nz+1) + (j-1)*(nz+1) + k;
                n2 = i*(ny+1)*(nz+1) + (j-1)*(nz+1) + k;
                n3 = i*(ny+1)*(nz+1) + j*(nz+1) + k;
                n4 = (i-1)*(ny+1)*(nz+1) + j*(nz+1) + k;
                
                elems(elem_idx, :) = [n1, n2, n3, n4, n1+1, n2+1, n3+1, n4+1];
                elem_idx = elem_idx + 1;
            end
        end
    end
    
    [node_coords, connectivity] = apply_square_hole(node_coords, elems, Lx, Ly, hole_params);
    
    mesh_info.num_nodes = size(node_coords, 1);
    mesh_info.num_elements = size(connectivity, 1);
    mesh_info.nodes_per_element = 8;
end


function [node_coords, connectivity, mesh_info] = generate_hexa20_mesh(Lx, Ly, Lz, nx, ny, nz, hole_params)
    [hex8_nodes, hex8_conn, ~] = generate_hexa8_mesh(Lx, Ly, Lz, nx, ny, nz, hole_params);
    
    num_hex8 = size(hex8_conn, 1);
    edge_map = containers.Map('KeyType', 'char', 'ValueType', 'any');
    mid_nodes_list = [];
    mid_node_counter = size(hex8_nodes, 1) + 1;
    
    connectivity = zeros(num_hex8, 20);
    
    edges = [1,2; 2,3; 3,4; 4,1; 5,6; 6,7; 7,8; 8,5; 1,5; 2,6; 3,7; 4,8];

    for e = 1:num_hex8
        corners = hex8_conn(e, :);
        mid_nodes = zeros(1, 12);
        for edge_idx = 1:12
            n1 = corners(edges(edge_idx, 1));
            n2 = corners(edges(edge_idx, 2));
            edge_key = sprintf('%d-%d', min(n1, n2), max(n1, n2));
            
            if isKey(edge_map, edge_key)
                mid_nodes(edge_idx) = edge_map(edge_key);
            else
                mid_nodes_list = [mid_nodes_list; (hex8_nodes(n1, :) + hex8_nodes(n2, :)) / 2.0];
                mid_nodes(edge_idx) = mid_node_counter;
                edge_map(edge_key) = mid_node_counter;
                mid_node_counter = mid_node_counter + 1;
            end
        end
        connectivity(e, :) = [corners, mid_nodes];
    end
    
    node_coords = [hex8_nodes; mid_nodes_list];
    
    mesh_info.num_nodes = size(node_coords, 1);
    mesh_info.num_elements = num_hex8;
    mesh_info.nodes_per_element = 20;
end

function [node_coords, connectivity, mesh_info] = generate_tet4_mesh(Lx, Ly, Lz, nx, ny, nz, hole_params)
    [hex_nodes, hex_conn, ~] = generate_hexa8_mesh(Lx, Ly, Lz, nx, ny, nz, hole_params);
    
    num_hex = size(hex_conn, 1);
    connectivity = zeros(num_hex * 5, 4);
    
    tet_count = 1;
    for h = 1:num_hex
        n = hex_conn(h, :);
        tets = [n(1), n(2), n(4), n(5);
                n(2), n(3), n(4), n(7);
                n(2), n(5), n(6), n(7);
                n(4), n(7), n(8), n(5);
                n(2), n(4), n(5), n(7)];
        connectivity(tet_count:tet_count+4, :) = tets;
        tet_count = tet_count + 5;
    end
    
    node_coords = hex_nodes;
    
    mesh_info.num_nodes = size(node_coords, 1);
    mesh_info.num_elements = size(connectivity, 1);
    mesh_info.nodes_per_element = 4;
end

function [node_coords, connectivity, mesh_info] = generate_tet10_mesh(Lx, Ly, Lz, nx, ny, nz, hole_params)
    [tet4_nodes, tet4_conn, ~] = generate_tet4_mesh(Lx, Ly, Lz, nx, ny, nz, hole_params);
    
    num_tet4 = size(tet4_conn, 1);
    edge_map = containers.Map('KeyType', 'char', 'ValueType', 'any');
    mid_nodes_list = [];
    mid_node_counter = size(tet4_nodes, 1) + 1;
    
    connectivity = zeros(num_tet4, 10);
    
    edges = [1,2; 2,3; 1,3; 1,4; 2,4; 3,4];

    for e = 1:num_tet4
        corners = tet4_conn(e, :);
        mid_nodes = zeros(1, 6);
        for edge_idx = 1:6
            n1 = corners(edges(edge_idx, 1));
            n2 = corners(edges(edge_idx, 2));
            edge_key = sprintf('%d-%d', min(n1, n2), max(n1, n2));
            
            if isKey(edge_map, edge_key)
                mid_nodes(edge_idx) = edge_map(edge_key);
            else
                mid_nodes_list = [mid_nodes_list; (tet4_nodes(n1, :) + tet4_nodes(n2, :)) / 2.0];
                mid_nodes(edge_idx) = mid_node_counter;
                edge_map(edge_key) = mid_node_counter;
                mid_node_counter = mid_node_counter + 1;
            end
        end
        connectivity(e, :) = [corners, mid_nodes];
    end
    
    node_coords = [tet4_nodes; mid_nodes_list];
    
    mesh_info.num_nodes = size(node_coords, 1);
    mesh_info.num_elements = num_tet4;
    mesh_info.nodes_per_element = 10;
end
