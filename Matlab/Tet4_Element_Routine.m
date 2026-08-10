function [Ke, Fb, Fs, Fl, F_total, C, Be_all] = Tet4_Element_Routine(Material, Coord, ~, ~)
% =========================================================================
% Tet4_Element_Routine: Computes matrices for a 4-node tetrahedral element.
% =========================================================================

    Ke = zeros(12, 12);
    Fb = zeros(12, 1);
    Fs = zeros(12, 1);
    Fl = zeros(12, 1);

    E = Material.E;
    nu = Material.nu;
    
    lambda_val = E*nu/((1+nu)*(1-2*nu));
    mu = E/(2*(1+nu));
    
    C = zeros(6, 6);
    C(1:3, 1:3) = lambda_val;
    for i = 1:3, C(i, i) = lambda_val + 2*mu; end
    C(4,4) = mu; C(5,5) = mu; C(6,6) = mu;

    n_order = 1; % 1-point integration for Tet4
    [g_pts, g_w] = GetGaussTableTetrahedra(n_order);
    Be_all = zeros(6, 12);

    for ig = 1:length(g_w)
        xi = g_pts(ig, 1);
        eta = g_pts(ig, 2);
        zeta = g_pts(ig, 3);
        w = g_w(ig) * (1.0 / 6.0);
        
        dN_nat = [-1, -1, -1; 1, 0, 0; 0, 1, 0; 0, 0, 1]';
        J = dN_nat * Coord;
        detJ = abs(det(J));
        dN_dx = J \ dN_nat;
        
        B = zeros(6, 12);
        for i = 1:4
            c = (i - 1) * 3 + 1;
            dx = dN_dx(1, i);
            dy = dN_dx(2, i);
            dz = dN_dx(3, i);
            
            B(1, c)     = dx;
            B(2, c+1)   = dy;
            B(3, c+2)   = dz;
            B(4, c:c+1)   = [dy, dx];
            B(5, c+1:c+2) = [dz, dy];
            B(6, [c, c+2]) = [dz, dx];
        end
        
        Be_all = B;
        Ke = Ke + (B' * C * B) * detJ * w;
    end

    F_total = Fb + Fs + Fl;
end


function [g_pts, g_w] = GetGaussTableTetrahedra(n)
    if n == 1
        g_pts = [0.25, 0.25, 0.25];
        g_w = 1.0;
    else % n == 4
        a = 0.58541020;
        b = 0.13819660;
        g_pts = [a, b, b; b, a, b; b, b, a; b, b, b];
        g_w = [0.25, 0.25, 0.25, 0.25];
    end
end
