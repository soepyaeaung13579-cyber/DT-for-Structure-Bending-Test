function [Ke, Fb, Fs, Fl, F_total, D, Be_all] = Hexa20_Element_Routine(Material, Coord, Loads, Settings)
% =========================================================================
% Hexa20_Element_Routine: Computes matrices for a 20-node hexahedral element.
% =========================================================================
    
    Ke = zeros(60, 60);
    Fb = zeros(60, 1);
    Fs = zeros(60, 1);
    Fl = zeros(60, 1);

    E = Material.E;
    nu = Material.nu;
    
    D_const = E / ((1 + nu) * (1 - 2 * nu));
    D = D_const * [
        1-nu, nu,   nu,   0, 0, 0;
        nu,   1-nu, nu,   0, 0, 0;
        nu,   nu,   1-nu, 0, 0, 0;
        0,    0,    0,    (1-2*nu)/2, 0, 0;
        0,    0,    0,    0, (1-2*nu)/2, 0;
        0,    0,    0,    0, 0, (1-2*nu)/2
    ];
    
    integration_mode = lower(Settings.Integration);
    
    if strcmp(integration_mode, '14point')
        num_gp = 14;
        a = 0.795822425754221;
        b = 0.758786910639328;
        w_a = 0.886421592695420;
        w_b = 0.335180055401662;
        
        gp_corners = [-a, -a, -a; a, -a, -a; a, a, -a; -a, a, -a; -a, -a, a; a, -a, a; a, a, a; -a, a, a];
        w_corners = ones(8, 1) * w_a;
        
        gp_axes = [-b, 0, 0; b, 0, 0; 0, -b, 0; 0, b, 0; 0, 0, -b; 0, 0, b];
        w_axes = ones(6, 1) * w_b;
        
        g_pts = [gp_corners; gp_axes];
        g_w = [w_corners; w_axes];
    else
        if strcmp(integration_mode, 'full')
            n_order = 3;
        else % reduced
            n_order = 2;
        end
        [g_pts, g_w] = BuildHexaGauss(n_order);
        num_gp = n_order^3;
    end
    
    Be_all = zeros(6 * num_gp, 60);
    gp_count = 1;
    
    for ig = 1:size(g_pts, 1)
        xi = g_pts(ig, 1);
        eta = g_pts(ig, 2);
        zeta = g_pts(ig, 3);
        w = g_w(ig);
        
        [~, dN_dxi, dN_deta, dN_dzeta] = Hexa20_ShapeFunctions(xi, eta, zeta);
        nat_derivs = [dN_dxi, dN_deta, dN_dzeta];
        J = nat_derivs' * Coord;
        
        detJ = det(J);
        if abs(detJ) < 1e-12, detJ = 1e-12; end
        
        dN_dx = nat_derivs * inv(J);
        
        B = zeros(6, 60);
        for n = 1:20
            c = (n - 1) * 3 + 1;
            dx = dN_dx(n, 1);
            dy = dN_dx(n, 2);
            dz = dN_dx(n, 3);
            
            B(1, c)     = dx;
            B(2, c+1)   = dy;
            B(3, c+2)   = dz;
            B(4, c:c+1)   = [dy, dx];
            B(5, c+1:c+2) = [dz, dy];
            B(6, [c, c+2]) = [dz, dx];
        end
        
        row_idx = (gp_count - 1) * 6;
        Be_all(row_idx+1 : row_idx+6, :) = B;
        
        Ke = Ke + (B' * D * B) * detJ * w;
        
        gp_count = gp_count + 1;
    end
    
    F_total = Fb + Fs + Fl;
end

function [N, dN_dxi, dN_deta, dN_dzeta] = Hexa20_ShapeFunctions(xi, eta, zeta)
    N = zeros(1, 20);
    dN_dxi = zeros(1, 20);
    dN_deta = zeros(1, 20);
    dN_dzeta = zeros(1, 20);
    
    pts = [-1, -1, -1; 1, -1, -1; 1, 1, -1; -1, 1, -1; -1, -1, 1; 1, -1, 1; 1, 1, 1; -1, 1, 1];
    ri = pts(:, 1)'; si = pts(:, 2)'; ti = pts(:, 3)';
    
    val = (1 + xi*ri) .* (1 + eta*si) .* (1 + zeta*ti);
    N(1:8) = 0.125 * val .* (xi*ri + eta*si + zeta*ti - 2);
    dN_dxi(1:8)   = 0.125 * ri .* (1+eta*si).*(1+zeta*ti) .* (2*xi*ri + eta*si + zeta*ti - 1);
    dN_deta(1:8)  = 0.125 * si .* (1+xi*ri).*(1+zeta*ti) .* (xi*ri + 2*eta*si + zeta*ti - 1);
    dN_dzeta(1:8) = 0.125 * ti .* (1+xi*ri).*(1+eta*si) .* (xi*ri + eta*si + 2*zeta*ti - 1);
    
    mid_coords = [0, -1, -1; 1, 0, -1; 0, 1, -1; -1, 0, -1;
                  0, -1, 1; 1, 0, 1; 0, 1, 1; -1, 0, 1;
                  -1, -1, 0; 1, -1, 0; 1, 1, 0; -1, 1, 0];
              
    for k = 1:12
        id_val = k + 8;
        ri_m = mid_coords(k, 1);
        si_m = mid_coords(k, 2);
        ti_m = mid_coords(k, 3);
        
        if ri_m == 0
            N(id_val)        = 0.25 * (1 - xi^2) * (1 + eta*si_m) * (1 + zeta*ti_m);
            dN_dxi(id_val)   = 0.25 * (-2*xi)     * (1 + eta*si_m) * (1 + zeta*ti_m);
            dN_deta(id_val)  = 0.25 * (1 - xi^2) * (si_m)         * (1 + zeta*ti_m);
            dN_dzeta(id_val) = 0.25 * (1 - xi^2) * (1 + eta*si_m) * (ti_m);
        elseif si_m == 0
            N(id_val)        = 0.25 * (1 + xi*ri_m) * (1 - eta^2) * (1 + zeta*ti_m);
            dN_dxi(id_val)   = 0.25 * (ri_m)        * (1 - eta^2) * (1 + zeta*ti_m);
            dN_deta(id_val)  = 0.25 * (1 + xi*ri_m) * (-2*eta)     * (1 + zeta*ti_m);
            dN_dzeta(id_val) = 0.25 * (1 + xi*ri_m) * (1 - eta^2) * (ti_m);
        elseif ti_m == 0
            N(id_val)        = 0.25 * (1 + xi*ri_m) * (1 + eta*si_m) * (1 - zeta^2);
            dN_dxi(id_val)   = 0.25 * (ri_m)        * (1 + eta*si_m) * (1 - zeta^2);
            dN_deta(id_val)  = 0.25 * (1 + xi*ri_m) * (si_m)         * (1 - zeta^2);
            dN_dzeta(id_val) = 0.25 * (1 + xi*ri_m) * (1 + eta*si_m) * (-2*zeta);
        end
    end
end

function [loc3, w3] = BuildHexaGauss(N)
    [loc1, w1] = GetGaussTable(N);
    [X, Y, Z] = meshgrid(loc1, loc1, loc1);
    [WX, WY, WZ] = meshgrid(w1, w1, w1);
    loc3 = [X(:), Y(:), Z(:)];
    w3 = WX(:) .* WY(:) .* WZ(:);
end
function [loc, w] = GetGaussTable(N)
    if N == 2
        loc = [-0.57735026919, 0.57735026919];
        w = [1.0, 1.0];
    elseif N == 3
        loc = [-0.774596669, 0.0, 0.774596669];
        w = [0.555555556, 0.888888889, 0.555555556];
    else % N == 1
        loc = 0.0;
        w = 2.0;
    end
end
