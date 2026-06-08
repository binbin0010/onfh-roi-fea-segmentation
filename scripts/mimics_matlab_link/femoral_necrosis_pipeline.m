%% femoral_necrosis_pipeline.m
% Femoral head necrosis ROI segmentation using Mimics 21 Research MATLAB Link.
%
% Inputs injected by Mimics MATLAB Link into the MATLAB base workspace:
%   V          - int16/uint16 3D volume matrix, usually GV = HU + 1024
%   MaskMatrix - logical 3D matrix for the active ALL_BONE mask
%   voxel      - [dx, dy, dz] voxel size in mm
%
% Output returned to Mimics:
%   NewMask    - logical 3D matrix for the final necrosis ROI
%
% This script does not require patient identifiers. Use an anonymized case ID.

%% User configuration

PATIENT_NAME = 'example_case';
OUTPUT_DIR = fullfile(pwd, 'outputs', 'mimics_matlab');
if ~exist(OUTPUT_DIR, 'dir'); mkdir(OUTPUT_DIR); end

% Mimics gray value (GV) = real HU + 1024.
GV_NECRO_MIN = 1034;  GV_NECRO_MAX = 1324;  % Necrotic core: real HU 10-300
GV_SCL_MIN   = 1624;  GV_SCL_MAX   = 2824;  % Sclerotic rim: real HU 600-1800

%% Seed-point input

prompt = {'Femoral-head center X (voxel index):', ...
          'Femoral-head center Y (voxel index):', ...
          'Femoral-head center Z (voxel index):', ...
          'Affected side (left/right):'};
dlgtitle = 'Femoral head seed point';
defaults = {num2str(round(size(V,2)/2)), ...
            num2str(round(size(V,1)/2)), ...
            num2str(round(size(V,3)*0.85)), ...
            'right'};
answer = inputdlg(prompt, dlgtitle, [1 50], defaults);
if isempty(answer); error('User cancelled.'); end

seed_x = str2double(answer{1});  % column direction, matrix dimension 2
seed_y = str2double(answer{2});  % row direction, matrix dimension 1
seed_z = str2double(answer{3});  % slice direction, matrix dimension 3
SIDE = lower(strtrim(answer{4}));

fprintf('=== Start processing: %s (side: %s) ===\n', PATIENT_NAME, SIDE);
fprintf('  CT size: %d x %d x %d, voxel %.3f x %.3f x %.3f mm\n', ...
    size(V,1), size(V,2), size(V,3), voxel(1), voxel(2), voxel(3));
fprintf('  Seed point (x,y,z) = (%d, %d, %d)\n', seed_x, seed_y, seed_z);

%% Step 1: femoral-head extraction by connected component and seed point

fprintf('[1/6] Extract femoral head by connected component\n');

% Morphological opening helps separate pelvis and femur when they touch.
SE_break = strel('sphere', 3);
all_bone_clean = imopen(MaskMatrix, SE_break);

CC = bwconncomp(all_bone_clean, 26);
seed_lin = sub2ind(size(MaskMatrix), seed_y, seed_x, seed_z);
fh_label = 0;

for k = 1:CC.NumObjects
    if any(CC.PixelIdxList{k} == seed_lin)
        fh_label = k;
        break;
    end
end

if fh_label == 0
    error(['Seed point is not inside any connected component. Check the seed ', ...
           'coordinates or reduce the opening radius from 3 to 2.']);
end

FEMORAL_HEAD = false(size(MaskMatrix));
FEMORAL_HEAD(CC.PixelIdxList{fh_label}) = true;

% Geometric head-neck separation: keep the superior 40% candidate band.
[~, ~, zs] = ind2sub(size(FEMORAL_HEAD), find(FEMORAL_HEAD));
z_top_fh = max(zs);
z_bot_fh = min(zs);
z_span_fh = z_top_fh - z_bot_fh;
z_cut_fh = z_top_fh - round(z_span_fh * 0.40);
FEMORAL_HEAD(:, :, 1:z_cut_fh) = false;

n_fh = nnz(FEMORAL_HEAD);
fprintf('      femoral-head voxels: %d (z range [%d, %d])\n', n_fh, z_cut_fh, z_top_fh);
if n_fh < 1000
    warning('Femoral-head voxel count is low (<1000). Check seed point and opening radius.');
end

%% Step 2: necrotic core by GV threshold within femoral head

fprintf('[2/6] Necrotic-core threshold (GV %d-%d)\n', GV_NECRO_MIN, GV_NECRO_MAX);
necro_raw = (V >= GV_NECRO_MIN) & (V <= GV_NECRO_MAX);
NECROTIC_CORE = necro_raw & FEMORAL_HEAD;
n_nec = nnz(NECROTIC_CORE);
fprintf('      necrotic-core voxels: %d\n', n_nec);

if n_nec == 0
    warning('Necrotic-core voxel count = 0.');
    warning('  Consider lowering GV_NECRO_MIN from 1034 to 924.');
    warning('  Also check whether Mimics exported real HU instead of GV.');
end

%% Step 3: sclerotic rim by GV threshold within femoral head

fprintf('[3/6] Sclerotic-rim threshold (GV %d-%d)\n', GV_SCL_MIN, GV_SCL_MAX);
scl_raw = (V >= GV_SCL_MIN) & (V <= GV_SCL_MAX);
SCLEROTIC_RIM = scl_raw & FEMORAL_HEAD;
fprintf('      sclerotic-rim voxels: %d\n', nnz(SCLEROTIC_RIM));

%% Step 4: morphological refinement to final ROI

fprintf('[4/6] Morphological refinement -> NECROSIS_ROI_FINAL\n');

SE_dil = strel('sphere', 3);
SE_close = strel('sphere', 4);
SCL_dilated = imdilate(SCLEROTIC_RIM, SE_dil) & FEMORAL_HEAD;
ROI = NECROTIC_CORE | SCL_dilated;
ROI = imclose(ROI, SE_close) & FEMORAL_HEAD;

for z = 1:size(ROI, 3)
    ROI(:,:,z) = imfill(ROI(:,:,z), 'holes');
end

fprintf('      final ROI voxels: %d\n', nnz(ROI));

%% Step 5: volume measurement

fprintf('[5/6] Volume measurement\n');
voxel_mm3 = prod(voxel);
vols = struct( ...
    'FEMORAL_HEAD',       nnz(FEMORAL_HEAD)  * voxel_mm3, ...
    'NECROTIC_CORE',      nnz(NECROTIC_CORE) * voxel_mm3, ...
    'SCLEROTIC_RIM',      nnz(SCLEROTIC_RIM) * voxel_mm3, ...
    'NECROSIS_ROI_FINAL', nnz(ROI)           * voxel_mm3);

if vols.FEMORAL_HEAD > 0
    ratio = vols.NECROSIS_ROI_FINAL / vols.FEMORAL_HEAD * 100;
else
    ratio = 0;
end

if ratio < 15 && vols.NECROSIS_ROI_FINAL < 1000
    arco = 'ARCO I';
elseif ratio < 15
    arco = 'ARCO I-II';
elseif ratio <= 30
    arco = 'ARCO II';
elseif ratio > 30
    arco = 'ARCO III-IV (review crescent sign)';
else
    arco = 'Unclassified';
end

%% Step 6: output report and return NewMask to Mimics

fprintf('[6/6] Output report\n');
report = sprintf([ ...
    '======================================================\n' ...
    '       Volume report - %s (side: %s)\n' ...
    '======================================================\n' ...
    '  FEMORAL_HEAD       : %10.2f mm^3\n' ...
    '  NECROTIC_CORE      : %10.2f mm^3\n' ...
    '  SCLEROTIC_RIM      : %10.2f mm^3\n' ...
    '  NECROSIS_ROI_FINAL : %10.2f mm^3\n' ...
    '  Necrosis ratio     : %10.2f %%\n' ...
    '  ARCO reference     : %s\n' ...
    '======================================================\n'], ...
    PATIENT_NAME, SIDE, ...
    vols.FEMORAL_HEAD, vols.NECROTIC_CORE, vols.SCLEROTIC_RIM, vols.NECROSIS_ROI_FINAL, ...
    ratio, arco);
fprintf('%s', report);

save(fullfile(OUTPUT_DIR, [PATIENT_NAME '_masks.mat']), ...
    'FEMORAL_HEAD', 'NECROTIC_CORE', 'SCLEROTIC_RIM', 'ROI', ...
    'vols', 'ratio', 'arco', 'voxel', '-v7.3');

fid = fopen(fullfile(OUTPUT_DIR, [PATIENT_NAME '_report.txt']), 'w');
fprintf(fid, '%s', report);
fclose(fid);

msgbox(report, ['Necrosis analysis report - ' PATIENT_NAME], 'help');

% Mimics MATLAB Link imports NewMask as a new mask after script completion.
NewMask = ROI;
fprintf('=== Done. NewMask will be returned to Mimics.\n');
fprintf('=== All masks saved to: %s\n', OUTPUT_DIR);
