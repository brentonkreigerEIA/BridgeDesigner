## Description

    # Geometric qualities
    # Constrained by Cable FOS, Sliding, Uplift
    # Optimized for excavation depth and cost

## Assumptions to Re-Evaluate

#0. ADD PENALTY FOR FOS CONSTRAINTS!
#0.5 ADD SAG OPTIMIZER INTO TOOL
#1. Ramp wall bottom is flat and meets foundation at bottom
#2. A 0.5 m tier means a 1 m foundation, a 1.5 m foundation means 1 m tiers. No other irregularities.
#3. No tower and foundation analyses
#4. Tiers are 0.5, 1, 2, 3, 3.5, and all "normal" sized
#5. Assume foundation is buried its full depth
#6. assume backwall goes just up to the soil height so soil height = anchor height + backwall height
#7. not including surcharge loads
#8. upper triangle of ramp is not considered for "extra" ramp area, this is currently a conservative estimation
#9. excavation is equally hard at all depths
#10. live load is not constrained
#11. Setback is 3m and 35 degree angle is assumed to be met so span is satisfied

## Imports
import pandas as pd
import sympy as sym
from sympy import Symbol
from sympy.core.relational import Relational
import mpmath as mp
import numpy as np
from scipy.optimize import minimize
from scipy.optimize import LinearConstraint

## Constant Variables

deck_width = 1.04  #meters
live_base = 4.07 #kN/m starting live load
tower_height = 1 #meters above walkway saddle
offset = 0.1 #meters
tier_offset = 25 #centimeters
W_suspenders = 0.0219  #kN/m
walkway_height = 0.4  #meters
ramp_thickness = 0.15 #meters
ramp_width = 3  #meters
backwall_thickness = 0.3  #meters
d_masonry = 2100 * 0.00980665  #kN/m3
d_concrete = 2400 * 0.00980665  #kN/m3
d_fill = 1900 * 0.00980665  #kN/m3
d_soil = 1800 * 0.00980665  #kN/m3
mu_saddle = 0.15  #unitless friction coefficient
base_wall_thickness = 0.3  #meters for 30 cm wall
Ptower = 30  # kN for tower weight
P_surcharge = 0
phi = 30  #internal friction angle
tower_volume = 2.492  #m3 this assumes the tower and walkway volume to be a constant
masonry_labor = 5 #m3 a day of masonry
fill_labor = 20 #m3 a day of fill
excavation_labor = 3 #m3 a day of excavation

    # Read in the file
path = '/Users/brentonkreiger/PycharmProjects/BridgeDesigner/venv/MasterInputs.xlsx'
Constants = pd.read_excel(path, sheet_name="Constants")

Span = Symbol('Span', real = True)  #delta h value in meters
SpanRange = Constants.iloc[7, 1]  #span range in meters
CableSize = Constants.iloc[0, 1]  #cable size in inches
WalkNumber = Constants.iloc[1, 1]  #walkway cable number
HandNumber = Constants.iloc[2, 1]  #handrail cable number
TotalCables = WalkNumber + HandNumber
LowSide = Constants.iloc[3, 1]  #Left or Right
design_sag_percent = Constants.iloc[6, 1]  #design sag percent
design_sag = design_sag_percent * Span
if SpanRange > 100:
    V_Anchor = 0.75  #vertical distance from where cable meets anchor to top of anchor (m)
    H_Anchor = 0.725  #horizontal distance from where cable meets anchor to front (m)
    anchor_height = 1.5  #anchor height in meters
    anchor_area = 2.175  #m2 anchor area
    b2 = 1.6  #m bottom of anchor dim
    b1 = 1.3  #m top of anchor dim
elif SpanRange <= 60:
    V_Anchor = 0.5
    H_Anchor = 0.475
    anchor_height = 1
    anchor_area = 0.95
    b2 = 1.1
    b1 = 0.8
else:
    V_Anchor = 0.65
    H_Anchor = 0.625
    anchor_height = 1.3
    anchor_area = 1.625
    b2 = 1.4
    b1 = 1.1

Lookups = pd.read_excel(path, sheet_name="Lookup")

CableArea = Lookups.iloc[0, 0]
A_cable = CableArea*TotalCables
W_crossbeams = Lookups.iloc[1, 0]
W_fencing = Lookups.iloc[2, 0]
W_deck = Lookups.iloc[3, 0]
W_cable = TotalCables*Lookups.iloc[4, 0]

W_dead = W_suspenders+W_cable+W_deck+W_fencing+W_crossbeams
walkway_area = Span*deck_width
live_reduced = live_base*(0.25 + (4.57/sym.sqrt(walkway_area)))
W_live = live_reduced * deck_width
w_TL = W_live + W_dead

## Variable Variables
DH = Symbol('DH', real = True)  #delta h value in meters
G2S_L = Symbol('G2S_L', real = True)  #ground to saddle total, left
G2S_R = Symbol('G2S_R', real = True)  #ground to saddle total, right
CL_L = Symbol('CL_L', real = True)  #backwall to center line, left
CL_R = Symbol('CL_R', real = True)  #backwall to center line, right
x1 = Symbol('x1', real = True)  #construction sag
x2 = Symbol('x2', real = True)  #hoisting sag
x4 = Symbol('x4', real = True)  #live sag
h_back_low = Symbol('h_back_low', real = True)  #back wall height meters
h_back_high = Symbol('h_back_high', real = True)  #back wall height meters

# FOS_CABLE= Symbol('FOS_CABLE', real = True)
# FOS_SLIDING_LOW = Symbol('FOS_SLIDING_LOW', real = True)
# FOS_SLIDING_HIGH = Symbol('FOS_SLIDING_HIGH', real = True)
# FOS_UPLIFT_LOW = Symbol('FOS_UPLIFT_LOW', real = True)
# FOS_UPLIFT_HIGH = Symbol('FOS_UPLIFT_HIGH', real = True)
# Freeboard = Symbol('Freeboard', real = True)

## Set up system of equations

    # Cable FOS
Ph = (w_TL * (Span**2)) / (8 * x4)

theta_low = sym.atan(((4 * x4) - DH) / Span)
theta_high = sym.atan(((4 * x4) + DH) / Span)
Pv_low = Ph * sym.tan(theta_low)
Pv_high = Ph * sym.tan(theta_high)
Pt_low = Ph / sym.cos(theta_low)
Pt_high = Ph / sym.cos(theta_high)

if LowSide == 'Left':
    alpha_hand_low = sym.atan((G2S_L + tower_height - V_Anchor) / (CL_L - H_Anchor))
    alpha_hand_high = sym.atan((G2S_R + tower_height - V_Anchor) / (CL_R - H_Anchor))
    alpha_walk_low = sym.atan((G2S_L - V_Anchor) / (CL_L - H_Anchor))
    alpha_walk_high = sym.atan((G2S_R- V_Anchor) / (CL_R - H_Anchor))
else:
    alpha_hand_low = sym.atan((G2S_R + tower_height - V_Anchor) / (CL_R - H_Anchor))
    alpha_hand_high = sym.atan((G2S_L + tower_height - V_Anchor) / (CL_L - H_Anchor))
    alpha_walk_low = sym.atan((G2S_R- V_Anchor) / (CL_R - H_Anchor))
    alpha_walk_high = sym.atan((G2S_L - V_Anchor) / (CL_L - H_Anchor))

Pt_back_hand_low = Ph / sym.cos(alpha_hand_low)
Pt_back_hand_high = Ph / sym.cos(alpha_hand_high)
Pt_back_walk_low = Ph / sym.cos(alpha_walk_low)
Pt_back_walk_high = Ph / sym.cos(alpha_walk_high)

Pv_back_hand_low = Pt_back_hand_low * sym.sin(alpha_hand_low)
Pv_back_hand_high = Pt_back_hand_high * sym.sin(alpha_hand_high)
Pv_back_walk_low = Pt_back_walk_high * sym.sin(alpha_walk_low)
Pv_back_walk_high = Pt_back_walk_high * sym.sin(alpha_walk_high)

Pt_main_low = Pt_low
Pt_main_high = Pt_high
Pv_main_low = Pt_main_low * sym.sin(theta_low)
Pv_main_high = Pt_main_high * sym.sin(theta_high)

R_tower_low = Pv_back_hand_low + Pv_main_low
R_tower_high = Pv_back_hand_high + Pv_main_high
max_force = Pt_back_hand_low
max_cable_tension = Lookups.iloc[5, 0]

FOS_CABLE = max_cable_tension / (max_force / TotalCables)

    # Uplift FOS
if LowSide == 'Left':
    area_low = (CL_L * (anchor_height + h_back_low)) + (0.5 * CL_L * (G2S_L - anchor_height - h_back_low))
    area_high = (CL_R * (anchor_height + h_back_low)) + (0.5 * CL_R * (G2S_L - anchor_height - h_back_low))
    tiers_low = Constants.iloc[8, 1]  #total height of tiers in meteres
    tiers_high = Constants.iloc[9, 1]  #total height of tiers in meteres
    ramp_angle_low = sym.atan((G2S_L - anchor_height - h_back_low) / CL_L)
    ramp_angle_high = sym.atan((G2S_R - anchor_height - h_back_low) / CL_R)
else:
    area_low = (CL_R * (anchor_height + h_back_low)) + (0.5 * CL_R * (G2S_L - anchor_height - h_back_low))
    area_high = (CL_L * (anchor_height + h_back_low)) + (0.5 * CL_L * (G2S_L - anchor_height - h_back_low))
    tiers_low = Constants.iloc[9, 1]
    tiers_high = Constants.iloc[8, 1]
    ramp_angle_low = sym.atan((G2S_R - anchor_height - h_back_low) / CL_R)
    ramp_angle_high = sym.atan((G2S_L - anchor_height - h_back_low) / CL_L)
uplift_x_low = (np.tan(np.radians(30)) * (anchor_height + h_back_low))  #x distance past anchor for overburden
uplift_x_high = (np.tan(np.radians(30)) * (anchor_height + h_back_high))  #x distance past anchor for overburden
uplift_y_low = (uplift_x_low + b2) * sym.tan(ramp_angle_low)
uplift_y_high = (uplift_x_high + b2) * sym.tan(ramp_angle_high)
ramplength_overburden_low = uplift_y_low / sym.sin(ramp_angle_low)
ramplength_overburden_high = uplift_y_high / sym.sin(ramp_angle_high)

overburden_area_low = (b2 * (anchor_height + h_back_low)) + (uplift_x_low * (anchor_height + h_back_low) * 0.5)+ ((uplift_x_low + b2) * (uplift_y_low) * 0.5)
overburden_area_high = (b2 * (anchor_height + h_back_high)) + (uplift_x_high * (anchor_height + h_back_high) * 0.5)+ ((uplift_x_high + b2) * (uplift_y_high) * 0.5)

if tiers_low < 1: #this means just one half tier
    H_tiers_low = 0.9 # 0.9 m off the centerline
    tiers_loss_low = (90 * 1) + ((90 - tier_offset) * tiers_low) + ((90 - (2 * tiers_offset)) * walkway_height)
    y_hand_low = 3 #distance to high siddle
elif tiers_low == 1:
    H_tiers_low = 0.9
    tiers_loss_low = (90 * 1) + ((90 - tier_offset) * tiers_low) + ((90 - (2 * tiers_offset)) * walkway_height)
    y_hand_low = 3.5
elif tiers_low == 2:
    H_tiers_low = 1.15
    tiers_loss_low = (115 * 1) + ((115 - (tier_offset * (tiers_low -1))) * 1) + ((115 - (tier_offset * tiers_low)) * 1) + ((115 - ((tiers_low+1) * tier_offset)) * walkway_height)
    y_hand_low = 4.5
elif tiers_low == 3:
    H_tiers_low = 1.4
    tiers_loss_low = (140 * 1) + ((140 - (tier_offset * (tiers_low - 2))) * 1) + ((140 - (tier_offset * (tiers_low - 1))) * 1) + ((140 - (tier_offset * tiers_low)) * 1) + ((140 - ((tiers_low + 1) * tier_offset)) * walkway_height)
    y_hand_low = 5.5
elif tiers_low > 3: #this means a 1.5 foundation tier
    H_tiers_low = 1.4
    tiers_loss_low = (140 * 1.5) + ((140 - (tier_offset * (tiers_low - 2))) * 1) + ((140 - (tier_offset * (tiers_low - 1))) * 1) + ((140 - (tier_offset * tiers_low)) * 1) + ((140 - ((tiers_low + 1) * tier_offset)) * walkway_height)
    y_hand_low = 6
if tiers_high < 1:  # this means just one half tier
    H_tiers_high = 0.9
    tiers_loss_high = (90 * 1) + ((90 - tier_offset) * tiers_low) + ((90 - (2 * tier_offset)) * walkway_height)
    y_hand_high = 3
elif tiers_high == 1:
    H_tiers_high = 0.9
    tiers_loss_high = (90 * 1) + ((90 - tier_offset) * tiers_low) + ((90 - (2 * tier_offset)) * walkway_height)
    y_hand_high = 3.5
elif tiers_high == 2:
    H_tiers_high = 1.15
    tiers_loss_high = (115 * 1) + ((115 - (tier_offset * (tiers_low - 1))) * 1) + ((115 - (tier_offset * tiers_low)) * 1) + ((115 - ((tiers_low + 1) * tier_offset)) * walkway_height)
    y_hand_high = 4.5
elif tiers_high == 3:
    H_tiers_high = 1.4
    tiers_loss_high = (140 * 1) + ((140 - (tier_offset * (tiers_low - 2))) * 1) + ((140 - (tier_offset * (tiers_low - 1))) * 1) + ((140 - (tier_offset * tiers_low)) * 1) + ((140 - ((tiers_low + 1) * tier_offset)) * walkway_height)
    y_hand_high = 5.5
elif tiers_high > 3:  # this means a 1.5 foundation tier
    H_tiers_high = 1.4
    tiers_loss_high = (140 * 1.5) + ((140 - (tier_offset * (tiers_low - 2))) * 1) + ((140 - (tier_offset * (tiers_low - 1))) * 1) + ((140 - (tier_offset * tiers_low)) * 1) + ((140 - ((tiers_low + 1) * tier_offset)) * walkway_height)
    y_hand_high = 6
if tiers_low > 3:
    ground_height_low = (H_Anchor + 1.5) / 2
else:
    ground_height_low = (H_Anchor + 1) / 2
if tiers_high > 3:
    ground_height_high = (H_Anchor + 1.5) / 2
else:
    ground_height_high = (H_Anchor + 1) / 2

if LowSide == 'Left':
    soil_area_low = (ground_height_low * (CL_L - H_tiers_low - b2))
    soil_area_high = (ground_height_high * (CL_R - H_tiers_high - b2))
    rampwall_area_low = area_low - (tiers_loss_low / 100) - anchor_area - soil_area_low   # ramp wall area in m2
    rampwall_area_high = area_high - (tiers_loss_high / 100) - anchor_area - soil_area_high # ramp wall area in m2
else:
    soil_area_low = (ground_height_low * (CL_R - H_tiers_low - b2))
    soil_area_high = (ground_height_high * (CL_L - H_tiers_high - b2))
    rampwall_area_low = area_high - (tiers_loss_high / 100) - anchor_area - soil_area_high
    rampwall_area_high = area_low - (tiers_loss_low / 100) - anchor_area - soil_area_low

    # concrete (ramp and anchor)
overburden_concrete_low = ((ramplength_overburden_low * ramp_thickness) + anchor_area) * ramp_width  #m3
overburden_concrete_high = ((ramplength_overburden_high * ramp_thickness) + anchor_area) * ramp_width
    # masonry (backwall)
overburden_masonry_low = (backwall_thickness * h_back_low) * ramp_width
overburden_masonry_high = (backwall_thickness * h_back_high) * ramp_width
    # rest of it
overburden_leftover_low = (overburden_area_low * ramp_width) - overburden_concrete_low - overburden_masonry_low
overburden_leftover_high = (overburden_area_high * ramp_width) - overburden_concrete_high - overburden_masonry_high

W_overburden_low =overburden_concrete_low * d_concrete + overburden_masonry_low * d_masonry + overburden_leftover_low * d_fill
W_overburden_high =overburden_concrete_high * d_concrete + overburden_masonry_high * d_masonry + overburden_leftover_high * d_fill
Vn_low = W_overburden_low
Vn_high = W_overburden_high

    #set up uplift forces
Pt_walk_tot_low = Pt_main_low * (WalkNumber/TotalCables)
Pt_walk_tot_high = Pt_main_high * (WalkNumber/TotalCables)
Pt_hand_tot_low = Pt_main_low * (HandNumber/TotalCables)
Pt_hand_tot_high = Pt_main_high * (HandNumber/TotalCables)

Pt_back_walk_belt_low = Pt_walk_tot_low * sym.exp((-mu_saddle) * (theta_low+alpha_walk_low + 0.04))
Pt_back_walk_belt_high = Pt_walk_tot_high * sym.exp((-mu_saddle) * (theta_high+alpha_walk_high + 0.04))
Pt_back_hand_belt_low = Pt_hand_tot_low * sym.exp((-mu_saddle) * (theta_low+alpha_hand_low + 0.04))
Pt_back_hand_belt_high = Pt_hand_tot_high * sym.exp((-mu_saddle) * (theta_high+alpha_hand_high + 0.04))

Pv_back_walk_belt_low = Pt_back_walk_belt_low * sym.sin(alpha_walk_low)
Pv_back_walk_belt_high = Pt_back_walk_belt_high * sym.sin(alpha_walk_high)
Pv_back_hand_belt_low = Pt_back_hand_belt_low * sym.sin(alpha_hand_low)
Pv_back_hand_belt_high = Pt_back_hand_belt_high * sym.sin(alpha_hand_high)

Ph_back_walk_belt_low = Pt_back_walk_belt_low * sym.cos(alpha_walk_low)
Ph_back_walk_belt_high = Pt_back_walk_belt_high * sym.cos(alpha_walk_high)
Ph_back_hand_belt_low = Pt_back_hand_belt_low * sym.cos(alpha_hand_low)
Ph_back_hand_belt_high = Pt_back_hand_belt_high * sym.cos(alpha_hand_high)

Pv_anchor_low = Pv_back_walk_belt_low + Pv_back_hand_belt_low
Pv_anchor_high = Pv_back_walk_belt_high + Pv_back_hand_belt_high
Vs_low = Pv_anchor_low
Vs_high = Pv_anchor_high

FOS_UPLIFT_LOW = Vn_low / Vs_low
FOS_UPLIFT_HIGH = Vn_high / Vs_high

    # Sliding FOS

    # Weight resisting forces (soil and ramp walls)

        #backwall
W_backwall_low = ramp_width * backwall_thickness * h_back_low * d_masonry  #kN
W_backwall_high = ramp_width * backwall_thickness * h_back_high * d_masonry

        #anchor
W_anchor = anchor_area * ramp_width * d_concrete  #kN

        #cap
W_rampcap_low = ramplength_overburden_low * ramp_thickness * ramp_width * d_masonry
W_rampcap_high = ramplength_overburden_high * ramp_thickness * ramp_width * d_masonry

        #rampwalls
area_ramp_low = area_low - soil_area_low - anchor_area - (backwall_thickness * h_back_low) - (ramplength_overburden_low * ramp_thickness) - tiers_loss_low
area_ramp_high = area_high - soil_area_high - anchor_area - (backwall_thickness * h_back_high) - (ramplength_overburden_high * ramp_thickness) - tiers_loss_high
            #if the tiers are 2, we want to subtract one meter down from the top
if LowSide == 'Left':
    upper_triangle = (G2S_L - anchor_height - h_back_low)
    upper_triangle_high = (G2S_R - anchor_height - h_back_high)
    if tiers_low == 2:
        W_extra_low = (anchor_height + h_back_low) * (CL_L - H_Anchor - (1.15/2)) * 0.2  # 1.15/2 is the average of how much tiers stick into the extra wall
    elif tiers_low > 2:
        W_extra_low = ((anchor_height + h_back_low) * (CL_L - H_Anchor - (1.4/2)) * 0.2) + ((anchor_height + h_back_low -1) * (CL_L - H_Anchor - (1.4/2)) * 0.2)
    else:
        W_extra_low = 0
    if tiers_high== 2:
        W_extra_high = (anchor_height + h_back_high) * (CL_R - H_Anchor - (1.15/2)) * 0.2
    elif tiers_low > 2:
        W_extra_high = ((anchor_height + h_back_high) * (CL_R - H_Anchor - (1.4/2)) * 0.2) + ((anchor_height + h_back_high -1) * (CL_R - H_Anchor - (1.4/2)) * 0.2)
    else:
        W_extra_high = 0
else:  #high side is left
    upper_triangle = (G2S_R - anchor_height - h_back_low)
    upper_triangle_high = (G2S_L - anchor_height - h_back_high)
    if tiers_low == 2:
        W_extra_low = (anchor_height + h_back_low) * CL_R * 0.2
    elif tiers_low > 2:
        W_extra_low = ((anchor_height + h_back_low) * CL_R * 0.2) + ((anchor_height + h_back_low -1) * CL_R * 0.2)
    else:
        W_extra_low = 0
    if tiers_high== 2:
        W_extra_high = (anchor_height + h_back_high) * CL_L * 0.2
    elif tiers_low > 2:
        W_extra_high = ((anchor_height + h_back_high) * CL_L * 0.2) + ((anchor_height + h_back_high -1) * CL_L * 0.2)
    else:
        W_extra_high = 0
    # Archive for future update
    # if tiers_low == 2:
    #     if upper_triangle > 1:   #if the upper triangle is deeper than 1
    #         extra_area_ramp_low = area_ramp_low - (0.5 * 1 * (1/sym.tan(ramp_angle_low)))
    #         W_extra_low = extra_area_ramp_low * 0.2  #assumes 50cm walls
    #     else:
    #         extra_area_ramp_low = area_ramp_low - (0.5 * upper_triangle * CL_R) - ((1 - upper_triangle) * CL_R)
    #         W_extra_low = extra_area_ramp_low * 0.2  # assumes 50cm walls
    # elif tiers_low == 3:
    #     if upper_triangle > 2:  #if the upper triangle is deeper than 1
    #         extra_area_ramp_low_50 = area_ramp_low - (0.5 * 1 * (1/sym.tan(ramp_angle_low)))
    #         extra_area_ramp_low_70 = area_ramp_low - (0.5 * 2 * (1/sym.tan(ramp_angle_low)))
    #         W_extra_low = extra_area_ramp_low_50 * 0.2 + extra_area_ramp_low_70 * 0.2
    #     elif upper_triangle < 1:
    #         extra_area_ramp_low_50 = area_ramp_low - (0.5 * upper_triangle * CL_R) - ((1 - upper_triangle) * CL_R)
    #         extra_area_ramp_low_70 = area_ramp_low - (0.5 * upper_triangle * CL_R) - ((2 - upper_triangle) * CL_R)
    #         W_extra_low = extra_area_ramp_low_50 * 0.2 + extra_area_ramp_low_70 * 0.2
    #     else:
    #         extra_area_ramp_low_50 = area_ramp_low - (0.5 * 1 * (1/sym.tan(ramp_angle_low)))
    #         extra_area_ramp_low_70 = area_ramp_low - (0.5 * upper_triangle * (1/sym.tan(ramp_angle_low))) - (0.5 * (2 - upper_triangle))
    #         W_extra_low = extra_area_ramp_low_50 * 0.2 + extra_area_ramp_low_70 * 0.2
    # elif tiers_low == 3.5:
    #     if upper_triangle > 2:  #if the upper triangle is deeper than 1
    #         extra_area_ramp_low_50 = area_ramp_low - (0.5 * 1 * (1/sym.tan(ramp_angle_low)))
    #         extra_area_ramp_low_70 = area_ramp_low - (0.5 * 2 * (1/sym.tan(ramp_angle_low)))
    #         W_extra_low = extra_area_ramp_low_50 * 0.2 + extra_area_ramp_low_70 * 0.2
    #     elif upper_triangle < 1:
    #         extra_area_ramp_low_50 = area_ramp_low - (0.5 * upper_triangle * CL_R) - ((1 - upper_triangle) * CL_R)
    #         extra_area_ramp_low_70 = area_ramp_low - (0.5 * upper_triangle * CL_R) - ((2 - upper_triangle) * CL_R)
    #         W_extra_low = extra_area_ramp_low_50 * 0.2 + extra_area_ramp_low_70 * 0.2
    #     else:
    #         extra_area_ramp_low_50 = area_ramp_low - (0.5 * 1 * (1/sym.tan(ramp_angle_low)))
    #         extra_area_ramp_low_70 = area_ramp_low - (0.5 * upper_triangle * (1/sym.tan(ramp_angle_low))) - (0.5 * (2 - upper_triangle))
    #         W_extra_low = extra_area_ramp_low_50 * 0.2 + extra_area_ramp_low_70 * 0.2
    # else:
    #     extra_area_ramp_low = 0
    # if tiers_high == 2:
    #     if upper_triangle_high > 1:  # if the upper triangle is deeper than 1
    #         extra_area_ramp_high = area_ramp_high - (0.5 * 1 * (1 / sym.tan(ramp_angle_high)))
    #         W_extra_high = extra_area_ramp_high * 0.2  # assumes 50cm walls
    #     else:
    #         extra_area_ramp_high = area_ramp_high - (0.5 * upper_triangle_high * CL_L) - ((1 - upper_triangle_high) * CL_L)
    #         W_extra_high = extra_area_ramp_high * 0.2  # assumes 50cm walls
    # elif tiers_high == 3:
    #     if upper_triangle_high > 2:  # if the upper triangle is deeper than 1
    #         extra_area_ramp_high_50 = area_ramp_high - (0.5 * 1 * (1 / sym.tan(ramp_angle_high)))
    #         extra_area_ramp_high_70 = area_ramp_high - (0.5 * 2 * (1 / sym.tan(ramp_angle_high)))
    #         W_extra_high = extra_area_ramp_high_50 * 0.2 + extra_area_ramp_high_70 * 0.2
    #     elif upper_triangle_high < 1:
    #         extra_area_ramp_high_50 = area_ramp_high - (0.5 * upper_triangle_high * CL_L) - ((1 - upper_triangle_high) * CL_L)
    #         extra_area_ramp_high_70 = area_ramp_high - (0.5 * upper_triangle_high * CL_L) - ((2 - upper_triangle_high) * CL_L)
    #         W_extra_high = extra_area_ramp_high_50 * 0.2 + extra_area_ramp_high_70 * 0.2
    #     else:
    #         extra_area_ramp_high_50 = area_ramp_high- (0.5 * 1 * (1 / sym.tan(ramp_angle_high)))
    #         extra_area_ramp_high_70 = area_ramp_high - (0.5 * upper_triangle_high * (1 / sym.tan(ramp_angle_high))) - (0.5 * (2 - upper_triangle_high))
    #         W_extra_high = extra_area_ramp_high_50 * 0.2 + extra_area_ramp_high_70 * 0.2
    # elif tiers_high == 3.5:
    #     if upper_triangle_high > 2:  # if the upper triangle is deeper than 1
    #         extra_area_ramp_high_50 = area_ramp_high - (0.5 * 1 * (1 / sym.tan(ramp_angle_high)))
    #         extra_area_ramp_high_70 = area_ramp_high - (0.5 * 2 * (1 / sym.tan(ramp_angle_high)))
    #         W_extra_high = extra_area_ramp_high_50 * 0.2 + extra_area_ramp_high_70 * 0.2
    #     elif upper_triangle_high < 1:
    #         extra_area_ramp_high_50 = area_ramp_high - (0.5 * upper_triangle_high * CL_L) - ((1 - upper_triangle_high) * CL_L)
    #         extra_area_ramp_high_70 = area_ramp_high - (0.5 * upper_triangle_high * CL_L) - ((2 - upper_triangle_high) * CL_L)
    #         W_extra_high = extra_area_ramp_high_50 * 0.2 + extra_area_ramp_high_70 * 0.2
    #     else:
    #         extra_area_ramp_high_50 = area_ramp_high - (0.5 * 1 * (1 / sym.tan(ramp_angle_high)))
    #         extra_area_ramp_high_70 = area_ramp_high - (0.5 * upper_triangle_high * (1 / sym.tan(ramp_angle_high))) - (0.5 * (2 - upper_triangle_high))
    #         W_extra_high = extra_area_ramp_high_50 * 0.2 + extra_area_ramp_high_70 * 0.2
    # else:
    #     extra_area_ramp_high = 0
W_ramp_low = (W_extra_low * d_masonry) + (area_ramp_low * base_wall_thickness * d_masonry)
W_ramp_high = (W_extra_high * d_masonry) + (area_ramp_high * base_wall_thickness * d_masonry)

        #fill
W_fill_low = (area_ramp_low * (ramp_width - (2 * base_wall_thickness)) * d_fill) + (soil_area_low * (ramp_width - (2 * base_wall_thickness)) * d_soil)  # Assume extra is built out not in to the fill and add soil
W_fill_high = (area_ramp_high * (ramp_width - (2 * base_wall_thickness)) * d_fill) + (soil_area_high * (ramp_width - (2 * base_wall_thickness)) * d_soil)

        #Tiers
if tiers_low < 1:
    W_tiers_low = ((4.42 * d_fill) + (7.36 * d_masonry)) + ((1.26 * d_fill) + (2.475 * d_masonry))
elif tiers_low == 1:
    W_tiers_low = ((4.42 * d_fill) + (7.36 * d_masonry)) + ((2.52 * d_fill) + (4.95 * d_masonry))
elif tiers_low == 2:
    W_tiers_low = ((4.42 * d_fill) + (7.36 * d_masonry)) + ((2.52 * d_fill) + (4.95 * d_masonry)) + ((6.58 * d_fill) + (10.03 * d_masonry))
elif tiers_low == 3:
    W_tiers_low = ((4.42 * d_fill) + (7.36 * d_masonry)) + ((2.52 * d_fill) + (4.95 * d_masonry)) + ((6.58 * d_fill) + (10.03 * d_masonry)) + ((9 * d_fill) + (12.96 * d_masonry))
elif tiers_low > 3:
    W_tiers_low = ((4.42 * d_fill) + (7.36 * d_masonry)) + ((2.52 * d_fill) + (4.95 * d_masonry)) + ((6.58 * d_fill) + (10.03 * d_masonry)) + ((13.5 * d_fill) + (19.44 * d_masonry))

if tiers_high < 1:
    W_tiers_high = ((4.42 * d_fill) + (7.36 * d_masonry)) + ((1.26 * d_fill) + (2.475 * d_masonry))
elif tiers_high == 1:
    W_tiers_high = ((4.42 * d_fill) + (7.36 * d_masonry)) + ((2.52 * d_fill) + (4.95 * d_masonry))
elif tiers_high == 2:
    W_tiers_high = ((4.42 * d_fill) + (7.36 * d_masonry)) + ((2.52 * d_fill) + (4.95 * d_masonry)) + ((6.58 * d_fill) + (10.03 * d_masonry))
elif tiers_high == 3:
    W_tiers_high = ((4.42 * d_fill) + (7.36 * d_masonry)) + ((2.52 * d_fill) + (4.95 * d_masonry)) + ((6.58 * d_fill) + (10.03 * d_masonry)) + ((9 * d_fill) + (12.96 * d_masonry))
elif tiers_high > 3:
    W_tiers_high = ((4.42 * d_fill) + (7.36 * d_masonry)) + ((2.52 * d_fill) + (4.95 * d_masonry)) + ((6.58 * d_fill) + (10.03 * d_masonry)) + ((13.5 * d_fill) + (19.44 * d_masonry))

Pabut_low = W_backwall_low + W_anchor + W_rampcap_low + W_ramp_low + W_fill_low + Ptower + W_tiers_low
Pabut_high = W_backwall_high + W_anchor + W_rampcap_high + W_ramp_high + W_fill_high + Ptower + W_tiers_high

    # Cable vertical forces (for)
Pv_tower_low = Pv_main_low + Pv_back_hand_belt_low + Pv_back_walk_belt_low
Pv_tower_high = Pv_main_high + Pv_back_hand_belt_low + Pv_back_walk_belt_low

    # Sidewall friction
if tiers_low > 3:
    Avg_Embedment_low = (1.5 + (h_back_low + anchor_height)) / 2
else:
    Avg_Embedment_low = (1 + (h_back_low + anchor_height))/2
if tiers_high > 3:
    Avg_Embedment_high = (1.5 + (h_back_high + anchor_height))/2
else:
    Avg_Embedment_high = (1 + (h_back_high + anchor_height)) / 2

if LowSide == 'Left':
    if tiers_low < 2:
        friction_area_low = Avg_Embedment_low * CL_L + (2.3 / 2) + 0.25
    elif tiers_low == 2:
        friction_area_low = Avg_Embedment_low * CL_L + (2.95 / 2) + 0.325
    elif tiers_low > 2:
        friction_area_low = Avg_Embedment_low * CL_L + (3.6 / 2) + 0.4
    if tiers_high < 2:
        friction_area_high = Avg_Embedment_high * CL_R + (2.3 / 2) + 0.25
    elif tiers_high == 2:
        friction_area_high = Avg_Embedment_high * CL_R + (2.95 / 2) + 0.325
    elif tiers_high > 2:
        friction_area_high = Avg_Embedment_high * CL_R + (3.6 / 2) + 0.4
else:
    if tiers_low < 2:
        friction_area_low = Avg_Embedment_low * CL_R + (2.3 / 2) + 0.25
    elif tiers_low == 2:
        friction_area_low = Avg_Embedment_low * CL_R + (2.95 / 2) + 0.325
    elif tiers_low > 2:
        friction_area_low = Avg_Embedment_low * CL_R + (3.6 / 2) + 0.4
    if tiers_high < 2:
        friction_area_high = Avg_Embedment_high * CL_L + (2.3 / 2) + 0.25
    elif tiers_high == 2:
        friction_area_high = Avg_Embedment_high * CL_L + (2.95 / 2) + 0.325
    elif tiers_high > 2:
        friction_area_high = Avg_Embedment_high * CL_L + (3.6 / 2) + 0.4

P_sidewall_low = 2 * (1 - sym.sin(mp.radians(phi))) * d_soil * (Avg_Embedment_low/2) * sym.tan(mp.radians(15)) * friction_area_low
P_sidewall_high = 2 * (1 - sym.sin(mp.radians(phi))) * d_soil * (Avg_Embedment_high/2) * sym.tan(mp.radians(15)) * friction_area_high

    # Sliding forces against
if LowSide == 'Left':
    B_low =  mp.radians(Constants.iloc[10, 1]) #soil profile slope in radians
    B_high = mp.radians(Constants.iloc[11, 1])
else:
    B_low = mp.radians(Constants.iloc[11, 1])
    B_high = mp.radians(Constants.iloc[10, 1])

Ka_low = sym.cos(B_low) * (sym.cos(B_low) - sym.sqrt((sym.cos(B_low)**2)-(sym.cos(mp.radians(phi))**2))) / (sym.cos(B_low) + sym.sqrt((sym.cos(B_low)**2)-(sym.cos(mp.radians(phi))**2)))
Ka_high = sym.cos(B_high) * (sym.cos(B_high) - sym.sqrt((sym.cos(B_high)**2)-(sym.cos(mp.radians(phi))**2))) / (sym.cos(B_high) + sym.sqrt((sym.cos(B_high)**2)-(sym.cos(mp.radians(phi))**2)))
P_active_low = 0.5 * Ka_low * d_soil * ((h_back_low + anchor_height)**2) * ramp_width
P_active_high = 0.5 * Ka_high * d_soil * ((h_back_high + anchor_height)**2) * ramp_width

Ph_tower_low = Ph - Ph_back_hand_belt_low - Ph_back_walk_belt_low
Ph_tower_high = Ph - Ph_back_hand_belt_high - Ph_back_walk_belt_high
Ph_anchor_low = Ph_back_hand_belt_low + Ph_back_walk_belt_low
Ph_anchor_high = Ph_back_hand_belt_high + Ph_back_walk_belt_high

Rs_low = Ph_anchor_low + Ph_tower_low + P_active_low + P_surcharge
Rs_high = Ph_anchor_high + Ph_tower_high + P_active_high + P_surcharge

    # Convert vertical forces to frictional resistance
sliding_coefficient = sym.tan(mp.radians(phi))

total_vertical_low = (Pabut_low + Pv_tower_low - Pv_anchor_low) * sliding_coefficient
total_vertical_high = (Pabut_high + Pv_tower_high - Pv_anchor_high) * sliding_coefficient
Rn_low = P_sidewall_low + total_vertical_low  #sliding resistance forces
Rn_high = P_sidewall_high + total_vertical_high

FOS_SLIDING_LOW = Rn_low / Rs_low
FOS_SLIDING_HIGH = Rn_high / Rs_high

# Calculate materials and costs

    # Materials
country = Constants.iloc[12, 1]

        # Cable
cable_left = CL_L - b1
cable_right = CL_R - b1
CableLength = TotalCables * 1.04 * (Span + cable_left + cable_right + 14 )

        # Cement
Rand2USD = 0.064
Bol2USD = 0.14
if country == 'Bolivia':
    cementperfill = 20  #kg/m3
    cementpermasonry = 80
    cementperconcrete = 350
    sandperconcrete = 0.6  #m3/m3
    sandpermasonry = 0.4
    sandperfill = 0.25
    gravelperconcrete = 0.6
    rockpermasonry = 0.8
    rockperfill = 0.95
    cost_cement = 57
    cost_sand = 250
    cost_gravel = 270
    cost_rock = 100
else:
    cementperfill = 36  #kg/m3
    cementpermasonry = 74.88
    cementperconcrete = 360
    sandperconcrete = 0.5  #m3/m3
    sandpermasonry = 0.208
    sandperfill = 0.1
    gravelperconcrete = 0.75
    rockpermasonry = 0.8
    rockperfill = 0.85
    cost_cement = 120.38
    cost_sand = 0  #no number, things less expensive in Eswatini
    cost_gravel = 195
    cost_rock = 0  #no number, things less expensive in Eswatini

if tiers_low < 1:
    M_tiers_low = ((4.42 * cementperfill) + (7.36 * cementpermasonry)) + ((1.26 * cementperfill) + (2.475 * cementpermasonry))
    R_tiers_low = ((4.42 * rockperfill) + (7.36 * rockpermasonry)) + ((1.26 * rockperfill) + (2.475 * rockpermasonry))
    S_tiers_low = ((4.42 * sandperfill) + (7.36 * sandpermasonry)) + ((1.26 * sandperfill) + (2.475 * sandpermasonry))
    E_tiers_low = 4.42 + 7.36
    L_tiers_low = 4.42 + 7.36 + 1.26 + 2.475
elif tiers_low == 1:
    M_tiers_low = ((4.42 * cementperfill) + (7.36 * cementpermasonry)) + ((2.52 * cementperfill) + (4.95 * cementpermasonry))
    R_tiers_low = ((4.42 * rockperfill) + (7.36 * rockpermasonry)) + ((2.52 * rockperfill) + (4.95 * rockpermasonry))
    S_tiers_low = ((4.42 * sandperfill) + (7.36 * sandpermasonry)) + ((2.52 * sandperfill) + (4.95 * sandpermasonry))
    E_tiers_low = 4.42 + 7.36
    L_tiers_low = 4.42 + 7.36 + 2.52 + 4.95
elif tiers_low == 2:
    M_tiers_low = ((4.42 * cementperfill) + (7.36 * cementpermasonry)) + ((2.52 * cementperfill) + (4.95 * cementpermasonry)) + ((6.58 * cementperfill) + (10.03 * cementpermasonry))
    R_tiers_low = ((4.42 * rockperfill) + (7.36 * rockpermasonry)) + ((2.52 * rockperfill) + (4.95 * rockpermasonry)) + ((6.58 * rockperfill) + (10.03 * rockpermasonry))
    S_tiers_low = ((4.42 * sandperfill) + (7.36 * sandpermasonry)) + ((2.52 * sandperfill) + (4.95 * sandpermasonry)) + ((6.58 * sandperfill) + (10.03 * sandpermasonry))
    E_tiers_low = 6.58 + 10.03
    L_tiers_low = 4.42 + 7.36 + 2.52 + 4.95 + 6.58 + 10.03
elif tiers_low == 3:
    M_tiers_low = ((4.42 * cementperfill) + (7.36 * cementpermasonry)) + ((2.52 * cementperfill) + (4.95 * cementpermasonry)) + ((6.58 * cementperfill) + (10.03 * cementpermasonry)) + ((9 * cementperfill) + (12.96 * cementpermasonry))
    R_tiers_low = ((4.42 * rockperfill) + (7.36 * rockpermasonry)) + ((2.52 * rockperfill) + (4.95 * rockpermasonry)) + ((6.58 * rockperfill) + (10.03 * rockpermasonry)) + ((9 * rockperfill) + (12.96 * rockpermasonry))
    S_tiers_low = ((4.42 * sandperfill) + (7.36 * sandpermasonry)) + ((2.52 * sandperfill) + (4.95 * sandpermasonry)) + ((6.58 * sandperfill) + (10.03 * sandpermasonry)) + ((9 * sandperfill) + (12.96 * sandpermasonry))
    E_tiers_low = 9 + 12.96
    L_tiers_low = 4.42 + 7.36 + 2.52 + 4.95 + 6.58 + 10.03 + 9 + 12.96
elif tiers_low > 3:
    M_tiers_low = ((4.42 * cementperfill) + (7.36 * cementpermasonry)) + ((2.52 * cementperfill) + (4.95 * cementpermasonry)) + ((6.58 * cementperfill) + (10.03 * cementpermasonry)) + ((13.5 * cementperfill) + (19.44 * cementpermasonry))
    R_tiers_low = ((4.42 * rockperfill) + (7.36 * rockpermasonry)) + ((2.52 * rockperfill) + (4.95 * rockperpermasonry)) + ((6.58 * rockperfill) + (10.03 * rockpermasonry)) + ((13.5 * rockperfill) + (19.44 * rockpermasonry))
    S_tiers_low = ((4.42 * sandperfill) + (7.36 * sandpermasonry)) + ((2.52 * sandperfill) + (4.95 * sandpermasonry)) + ((6.58 * sandperfill) + (10.03 * sandpermasonry)) + ((13.5 * sandperfill) + (19.44 * sandpermasonry))
    E_tiers_low = 13.5 + 19.44
    L_tiers_low = 4.42 + 7.36 + 2.52 + 4.95 + 6.58 + 10.03 + 13.5 + 19.44
if tiers_high < 1:
    M_tiers_high = ((4.42 * cementperfill) + (7.36 * cementpermasonry)) + ((1.26 * cementperfill) + (2.475 * cementpermasonry))
    R_tiers_high = ((4.42 * rockperfill) + (7.36 * rockpermasonry)) + ((1.26 * rockperfill) + (2.475 * rockpermasonry))
    S_tiers_high = ((4.42 * sandperfill) + (7.36 * sandpermasonry)) + ((1.26 * sandperfill) + (2.475 * sandpermasonry))
    E_tiers_high = 4.42 + 7.36
    L_tiers_high = 4.42 + 7.36 + 1.26 + 2.475
elif tiers_high == 1:
    M_tiers_high = ((4.42 * cementperfill) + (7.36 * cementpermasonry)) + ((2.52 * cementperfill) + (4.95 * cementpermasonry))
    R_tiers_high = ((4.42 * rockperfill) + (7.36 * rockpermasonry)) + ((2.52 * rockperfill) + (4.95 * rockpermasonry))
    S_tiers_high = ((4.42 * sandperfill) + (7.36 * sandpermasonry)) + ((2.52 * sandperfill) + (4.95 * sandpermasonry))
    E_tiers_high = 4.42 + 7.36
    L_tiers_high = 4.42 + 7.36 + 2.52 + 4.95
elif tiers_high == 2:
    M_tiers_high = ((4.42 * cementperfill) + (7.36 * cementpermasonry)) + ((2.52 * cementperfill) + (4.95 * cementpermasonry)) + ((6.58 * cementperfill) + (10.03 * cementpermasonry))
    R_tiers_high = ((4.42 * rockperfill) + (7.36 * rockpermasonry)) + ((2.52 * rockperfill) + (4.95 * rockpermasonry)) + ((6.58 * rockperfill) + (10.03 * rockpermasonry))
    S_tiers_high = ((4.42 * sandperfill) + (7.36 * sandpermasonry)) + ((2.52 * sandperfill) + (4.95 * sandpermasonry)) + ((6.58 * sandperfill) + (10.03 * sandpermasonry))
    E_tiers_high = 6.58 + 10.03
    L_tiers_high = 4.42 + 7.36 + 2.52 + 4.95 + 6.58 + 10.03
elif tiers_high == 3:
    M_tiers_high = ((4.42 * cementperfill) + (7.36 * cementpermasonry)) + ((2.52 * cementperfill) + (4.95 * cementpermasonry)) + ((6.58 * cementperfill) + (10.03 * cementpermasonry)) + ((9 * cementperfill) + (12.96 * cementpermasonry))
    R_tiers_high = ((4.42 * rockperfill) + (7.36 * rockpermasonry)) + ((2.52 * rockperfill) + (4.95 * rockpermasonry)) + ((6.58 * rockperfill) + (10.03 * rockpermasonry)) + ((9 * rockperfill) + (12.96 * rockpermasonry))
    S_tiers_high = ((4.42 * sandperfill) + (7.36 * sandpermasonry)) + ((2.52 * sandperfill) + (4.95 * sandpermasonry)) + ((6.58 * sandperfill) + (10.03 * sandpermasonry)) + ((9 * sandperfill) + (12.96 * sandpermasonry))
    E_tiers_high = 9 + 12.96
    L_tiers_high = 4.42 + 7.36 + 2.52 + 4.95 + 6.58 + 10.03 + 9 + 12.96
elif tiers_high > 3:
    M_tiers_high = ((4.42 * cementperfill) + (7.36 * cementpermasonry)) + ((2.52 * cementperfill) + (4.95 * cementpermasonry)) + ((6.58 * cementperfill) + (10.03 * cementpermasonry)) + ((13.5 * cementperfill) + (19.44 * cementpermasonry))
    R_tiers_high = ((4.42 * rockperfill) + (7.36 * rockpermasonry)) + ((2.52 * rockperfill) + (4.95 * rockpermasonry)) + ((6.58 * rockperfill) + (10.03 * rockpermasonry)) + ((13.5 * rockperfill) + (19.44 * rockpermasonry))
    S_tiers_high = ((4.42 * sandperfill) + (7.36 * sandpermasonry)) + ((2.52 * sandperfill) + (4.95 * sandpermasonry)) + ((6.58 * sandperfill) + (10.03 * sandpermasonry)) + ((13.5 * sandperfill) + (19.44 * sandpermasonry))
    E_tiers_high = 13.5 + 19.44
    L_tiers_high = 4.42 + 7.36 + 2.52 + 4.95 + 6.58 + 13.5 + 9 + 19.44

M_tiers = ((M_tiers_low + M_tiers_high) / 50)  #value in 50 kg bags

M_ramp_low = (W_extra_low + (area_ramp_low * base_wall_thickness))* cementpermasonry  #W_extra is actually a volume
M_ramp_high = (W_extra_high + (area_ramp_high * base_wall_thickness))* cementpermasonry
M_ramp = (M_ramp_low + M_ramp_high) / 50

M_fill_low = area_ramp_low * (ramp_width - (2 * base_wall_thickness)) * cementperfill
M_fill_high = area_ramp_high * (ramp_width - (2 * base_wall_thickness)) * cementperfill
M_fill = (M_fill_low + M_fill_high) / 50

M_cap_low = ramplength_overburden_low * ramp_thickness * ramp_width * cementperconcrete
M_cap_high = ramplength_overburden_high * ramp_thickness * ramp_width * cementperconcrete
M_cap = (M_cap_low + M_cap_high) / 50

M_anchor = 2 * anchor_area * ramp_width * cementperconcrete / 50

M_towers = (tower_volume * cementperconcrete)/ 50  #2.492 m3 is tower volume number, assume this is constant

Cement = M_tiers + M_ramp + M_fill + M_cap + M_anchor + M_towers  #value in 50 kg bags

        # Rocks
R_tiers = R_tiers_high + R_tiers_low
R_masonry = (W_extra_low + W_extra_high + (area_ramp_low * base_wall_thickness) + (area_ramp_high * base_wall_thickness))* rockpermasonry
R_fill = (area_ramp_low * (ramp_width - (2 * base_wall_thickness)) + area_ramp_high * (ramp_width - (2 * base_wall_thickness))) * rockperfill
Rocks = R_tiers + R_masonry + R_fill

        # Sand
S_tiers = S_tiers_high + S_tiers_low
S_masonry = (W_extra_low + W_extra_high + (area_ramp_low * base_wall_thickness) + (area_ramp_high * base_wall_thickness))* sandpermasonry
S_fill = (area_ramp_low * (ramp_width - (2 * base_wall_thickness)) + area_ramp_high * (ramp_width - (2 * base_wall_thickness))) * sandperfill
S_concrete = (tower_volume * sandperconcrete) + (2 * anchor_area * ramp_width * sandperconcrete)
Sand = S_tiers + S_masonry + S_fill + S_concrete

        # Gravel
Gravel = (tower_volume * gravelperconcrete) + (2 * anchor_area * ramp_width * gravelperconcrete)

    # Labor (this assumes the anchor, decking and tensioning is the same, only looking into tiers, walls, and excavations

        #Excavation
Footprint_Excavation = ((soil_area_low + soil_area_high) * ramp_width) + (V_Anchor * ramp_width * b2 * 2) + E_tiers_low + E_tiers_high
        #Ramp and Tiers
Labor_Tiers = L_tiers_low + L_tiers_high
Labor_RampWalls = (area_ramp_low + area_ramp_high) * base_wall_thickness + (W_extra_high + W_extra_low)
Labor_RampFill = (area_ramp_high + area_ramp_low) * (ramp_width - 2 * base_wall_thickness)

    # Cost

        #Labor (Excavation, Masonry)
pay = 40  # 40$ a day per mason
            # assume that one mason takes 4 days to do about one tier or 15 m3 of masonry, 10 hour days
Labor_Cost = ((Labor_Tiers/masonry_labor) * pay) + ((Labor_RampWalls/masonry_labor) * pay) + ((Labor_RampFill/fill_labor) * pay) + ((Footprint_Excavation/excavation_labor) * pay)

        #Materials by price (Cement, Rocks, Sand, Gravel)
Material_Cost = Cement * cost_cement + Rocks * cost_rock + Sand * cost_sand + Gravel * cost_gravel

## Set up constraints (https://docs.scipy.org/doc/scipy/reference/tutorial/optimize.html#constrained-minimization-of-multivariate-scalar-functions-minimize)
x_fnd_L = Constants.iloc[13, 1]
x_fnd_R = Constants.iloc[14, 1]
y_fnd_L = Constants.iloc[15, 1]
y_fnd_R = Constants.iloc[16, 1]
HWL = Constants.iloc[17, 1]
f = (((4 * x4) - DH)**2)/(16 * x4)

if LowSide == 'Left':
    Freeboard = y_fnd_L + y_hand_low - (f + HWL)
else:
    Freeboard = y_fnd_R + y_hand_low - (f + HWL)

#STOPPED HERE
    #Create penalty terms but conditionals don't work because of symbols
# cable_penalty = FOS_CABLE - 3
# penalty = cable_penalty + sliding_low_penalty + sliding_high_penalty + uplift_high_penalty + uplift_low_penalty + freeboard_penalty + delta_penalty

        # variable order is Span, DH, G2S_L, G2S_R, CL_L, CL_R, x1, x2, x4, h_back_low, h_back_high
# bounds = Bounds([0, 120], [0, 10], [0, 5], [0, 5], [0, 15], [0, 15], [0, 10], [0, 10], [0, 10], [0, 5], [0, 5])
linear_constraint = LinearConstraint([[1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
                      [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
                      [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
                      [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                     [120, 10, 5, 5, 15, 15, 10, 10, 10, 5, 5])

## Solve for minimal "cost" with safety and serviceability constraints.
Cost = Material_Cost + Labor_Cost # + penalty
Cost_function = sym.lambdify([(Span, DH, G2S_L, G2S_R, CL_L, CL_R, x1, x2, x4, h_back_low, h_back_high)], Cost)

## Minimize
x0 = np.array([60, 3, 3, 3, 10, 10, 2, 3, 4, 1, 1])
res = minimize(Cost_function, x0, method='trust-constr', constraints=[linear_constraint], options={'verbose': 1})

print('Span is ' + str(np.floor(res.x[0])) + ' meters')
print('DH is ' + str(np.floor(res.x[1])) + ' meters')
print('G2S_L is ' + str(np.floor(res.x[2])) + ' meters')
print('G2S_R is ' + str(np.floor(res.x[3])) + ' meters')
print('CL_L is ' + str(np.floor(res.x[4])) + ' meters')
print('CL_R is ' + str(np.floor(res.x[5])) + ' meters')
print('hoisting sag is ' + str(np.floor(res.x[6])) + ' meters')
print('design sag is ' + str(np.floor(res.x[7])) + ' meters')
print('live load sag is ' + str(np.floor(res.x[8])) + ' meters')
print('backwall height low is ' + str(np.floor(res.x[9])) + ' meters')
print('backwall height high is ' + str(np.floor(res.x[10])) + ' meters')

## Present Solution (graphically, numerically)